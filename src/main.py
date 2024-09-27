import os
import json

from dotenv import load_dotenv
load_dotenv()

from llm import get_ollama_llm, get_gpt_llm
from prompts import SYSTEM_PROMPT, parser, get_tool_by_name
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from tools.tools import PROJECT_ROOT

import logging

logging.basicConfig(level=logging.INFO)

class CodeRefactoringAgent:
    
    def __init__(self, project):
        self._logger = logging.getLogger("CodeRefactoringAgent")

        self._project = project
        self._history = [SYSTEM_PROMPT]
        self._model = get_gpt_llm()
        
        self._logger.info(f"Initialized with project {project}")


    def run(self):

        while True:
            response = self._model.invoke(self._history)

            try:
                response = parser.parse(response.content)
            except Exception:
                msg = "Output could not be parsed. Make sure to respond in the correct format."
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=msg + " " + parser.get_format_instructions()))
                continue
            thought, action, action_input, observation = response.thought, response.action, response.tools_input, response.observation
            
            # we don't want to store the full response in the history to keep the context window small
            self._history.append(AIMessage(content=json.dumps({
                "thought": thought,
                "action": action,
                "observation": observation,
            }, indent=4)))

            self._logger.info(f"Thought: {thought}")
            self._logger.info(f"Action: {action}") # , Input: {action_input}")
            self._logger.info(f"Observation: {observation}")

            tool = get_tool_by_name(action)
            if tool is None:
                msg = f"Tool {action} not found."
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=msg))
                continue

            try:
                tool_result = tool.invoke(action_input)
                self._logger.info(f"Tool {action} executed.")
                self._history.append(HumanMessage(content=f"Tool {action} replies: {tool_result}"))

            except Exception as e:
                msg = f"Tool {action} could not be executed: {str(e)}"
                self._logger.warning(msg)
                self._history.append(HumanMessage(content=msg))
            print("========================================")

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("Application started.")

    project = os.path.join(PROJECT_ROOT, "sample_project")
    CodeRefactoringAgent(project).run()
