import os
import json

from dotenv import load_dotenv
load_dotenv()

from llm import get_ollama_llm, get_gpt_llm
from prompts import get_system_message, ReActOutput, parser, get_tool_by_name
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from tools.tools import PROJECT_ROOT

import logging

logging.basicConfig(level=logging.INFO)

NEWLINE = "\n"

def prettify_list(l: list[str]) -> str:
    list_items_w_tab_and_bullet = ["\t- " + step for step in l]
    return NEWLINE.join(list_items_w_tab_and_bullet)


class CodeRefactoringAgent:

    def __init__(self, project):
        self._logger = logging.getLogger("CodeRefactoringAgent")

        self._project = project
        self._history = [get_system_message()]
        self._model = get_gpt_llm()

        self._logger.info(f"Initialized with project {project}")

    def _log_agent_message(self, response: ReActOutput):
        self._logger.info("Plan:\n" + prettify_list(response.plan))
        self._logger.info(f"Thought: {response.thought}")
        self._logger.info(f"Action: {response.action}")
        self._logger.info(f"Observation: {response.observation}")
        self._logger.info(f"Problems:\n" + prettify_list(response.problems))

    def _add_to_history(self, response: ReActOutput):
        # we don't want to store the full response in the history to keep the context window small
        self._history.append(AIMessage(content=json.dumps({
            "thought": response.thought,
            "action": response.action,
            "tools_input": response.tools_input,
            "observation": response.observation,
            "plan": response.plan,
            "problems": response.problems
        }, indent=4)))


    def run(self):

        while True:
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

            tool = get_tool_by_name(response.action)
            if tool is None:
                msg = f"Tool {response.action} not found."
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=msg))
                continue

            try:
                tool_result = tool.invoke(response.tools_input)
                self._logger.info(f"Tool {response.action} executed.")
                self._history.append(HumanMessage(content=f"Tool {response.action} replies: {tool_result}"))

            except Exception as e:
                msg = f"Tool {response.action} could not be executed: {str(e)}"
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=msg))

            # if we've committed changes, we want to clean the history    
            if response.action == "commit_changes":
                self._history = [get_system_message()]
                self._add_to_history(response)
                self._logger.info("Committed changes. Cleaning history.")

            print("========================================")

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("Application started.")

    project = os.path.join(PROJECT_ROOT, "sample_project")
    CodeRefactoringAgent(project).run()
