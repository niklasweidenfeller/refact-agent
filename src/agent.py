import json
import logging
import uuid
import os

from langchain_core.messages import AIMessage, HumanMessage
import tiktoken

from llm import get_gpt_llm
from prompts import get_system_message, ReActOutput, parser, build_tool_info
from tools.git_tools import git_checkout
from tools.registry import register_tools
from utils import prettify_list

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 20))
MAX_CONSECUTIVE_ERRORS = int(os.getenv("MAX_CONSECUTIVE_ERRORS", 3))
CONTEXT_LIMIT = int(os.getenv("CONTEXT_LIMIT", 15_000))

ENCODER = tiktoken.encoding_for_model("gpt-4o")


class CodeRefactoringAgent:

    def __init__(self, project, directory):
        self._logger = logging.getLogger("CodeRefactoringAgent")

        self._tool_registry = register_tools(project, directory)
        self._project = project
        self._history = [get_system_message(self._tool_registry)]
        self._model = get_gpt_llm()

        self._logger.info(f"Initialized with project {project}")
        
        self._consecutive_error_count = 0

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

    def _estimate_tokens(self):
        total_token_ct = 0
        for message in self._history:
            msg_tokens = ENCODER.encode(message.content)
            total_token_ct += len(msg_tokens)
        return total_token_ct

    def _clip_message_history(self, token_limit):
        current_token_ct = self._estimate_tokens()
        if current_token_ct <= token_limit:
            self._logger.info(f"Current token count {current_token_ct} is below limit {token_limit}.")
            return

        all_messages = self._history.copy()
        self._history = [all_messages.pop(0)]
        while self._estimate_tokens() <= token_limit:
            if len(all_messages) == 0:
                break
            most_recent_remaining_message = all_messages.pop()
            if len(self._history) == 1:
                self._history.append(most_recent_remaining_message)
            else:
                # message needs to be inserted after the first message
                self._history.insert(1, most_recent_remaining_message)
        self._logger.info(f"Clipped message history to {self._estimate_tokens()} tokens (limit: {token_limit}).")

    def run(self):

        self._working_branch = "ReFAct-" + str(uuid.uuid4())
        git_checkout(self._working_branch, create=True)

        num_commits = 0
        while num_commits < MAX_ITERATIONS:
            """
            Note: This loop does not have a termination condition,
            as the agent should terminate by calling the "stop" tool.
            """

            self._clip_message_history(token_limit=CONTEXT_LIMIT)


            # if the agent seems stuck, we'll try to reset the state
            if self._consecutive_error_count >= MAX_CONSECUTIVE_ERRORS:
                self._consecutive_error_count = 0
                self._history = [get_system_message(self._tool_registry)]
            response = self._model.invoke(self._history)

            try:
                response = parser.parse(response.content)
            except Exception:
                self._consecutive_error_count += 1
                msg = "Output could not be parsed. Make sure to respond in the correct format."
                self._logger.warning(msg)
                self._history.append(response)
                self._history.append(HumanMessage(content=f"{msg} {parser.get_format_instructions()}"))
                continue

            self._add_to_history(response)
            self._log_agent_message(response)

            tool = self._get_tool_by_name(response.action)
            if tool is None:
                self._consecutive_error_count += 1
                msg = f"Tool {response.action} not found."
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=f"{msg} Available tools: {build_tool_info(self._tool_registry)}"))
                continue

            try:
                tool_result = tool.invoke(response.tools_input)
                self._logger.info(f"Tool {response.action} executed.")
                self._history.append(HumanMessage(content=f"Tool {response.action} replies: {tool_result}"))

                # increase the count of successful commits
                if response.action == "commit_changes":
                    num_commits += 1

            except Exception as e:
                self._consecutive_error_count += 1
                msg = f"Tool {response.action} could not be executed: {str(e)}"
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=msg))

            print("========================================")

        self._logger.info(
            "Maximum number of commits reached without calling the 'stop' tool. Terminating."
        )
