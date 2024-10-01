import json
import logging
import uuid
import os

from llm import get_gpt_llm
from prompts import get_system_message, ReActOutput, parser
from langchain_core.messages import AIMessage, HumanMessage

from tools.git_tools import git_checkout
from tools.registry import register_tools
from utils import prettify_list

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 20))



class CodeRefactoringAgent:

    def __init__(self, project, directory):
        self._logger = logging.getLogger("CodeRefactoringAgent")

        self._tool_registry = register_tools(project, directory)
        self._project = project
        self._history = [get_system_message(self._tool_registry)]
        self._model = get_gpt_llm()

        self._logger.info(f"Initialized with project {project}")

    def _log_agent_message(self, response: ReActOutput):
        # self._logger.info("Plan:\n" + prettify_list(response.plan))
        self._logger.info(f"Thought: {response.thought}")
        self._logger.info(f"Action: {response.action}")
        self._logger.info(f"Observation: {response.observation}")
        self._logger.info(f"Issues:\n {prettify_list(response.issues)}")

    def _add_to_history(self, response: ReActOutput):
        # we don't want to store the full response in the history to keep the context window small
        self._history.append(AIMessage(content=json.dumps({
            "thought": response.thought,
            "action": response.action,
            "tools_input": response.tools_input,
            "observation": response.observation,
            # "plan": response.plan,
            "issues": response.issues
            # "problems": response.problems
        }, indent=4)))


    def _get_tool_by_name(self, name):
        for tool in self._tool_registry:
            if tool.name == name:
                return tool
        return None

    def run(self):
        
        self._working_branch = "ReFAct-" + str(uuid.uuid4())
        git_checkout(self._working_branch, create=True)

        num_commits = 0
        while num_commits < MAX_ITERATIONS:
            """
            Note: This loop does not have a termination condition,
            as the agent should terminate by calling the "stop" tool.
            """

            response = self._model.invoke(self._history)

            try:
                response = parser.parse(response.content)
            except Exception:
                msg = "Output could not be parsed. Make sure to respond in the correct format."
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=msg + " " + parser.get_format_instructions()))
                continue

            self._add_to_history(response)
            self._log_agent_message(response)

            tool = self._get_tool_by_name(response.action)
            if tool is None:
                msg = f"Tool {response.action} not found."
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=msg))
                continue

            try:
                tool_result = tool.invoke(response.tools_input)
                self._logger.info(f"Tool {response.action} executed.")
                self._history.append(HumanMessage(content=f"Tool {response.action} replies: {tool_result}"))

                # increase the count of successful commits
                if response.action == "commit_changes":
                    num_commits += 1

            except Exception as e:
                msg = f"Tool {response.action} could not be executed: {str(e)}"
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=msg))

            print("========================================")

        self._logger.info(
            "Maximum number of commits reached without calling the 'stop' tool. Terminating."
        )
