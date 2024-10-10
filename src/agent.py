""" Contains the Agent class containing the run method. """

import json
import logging
import uuid
import os

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.exceptions import OutputParserException
from langchain_openai.chat_models.base import BaseChatOpenAI
import tiktoken

from .config import get_settings
from .llm import get_llm
from .prompts import PlanReActOutput, get_system_message, ReActOutput, parser, build_tool_info
from .tools.git_tools import git_checkout
from .tools.registry import register_tools
from .utils import prettify_list

HARD_MAX_ITERATIONS = 20

MAX_NUM_OF_COMMITS = int(os.getenv("MAX_ITERATIONS", "5"))
MAX_CONSECUTIVE_ERRORS = int(os.getenv("MAX_CONSECUTIVE_ERRORS", "3"))
CONTEXT_LIMIT = int(os.getenv("CONTEXT_LIMIT", "8192"))
LOG_FILE_DIR = "logs"

ENCODER = tiktoken.encoding_for_model("gpt-4o")


class CodeRefactoringAgent:
    """ The Agent class containing the run method. """
    # pylint: disable=too-few-public-methods

    def __init__(self, project, directory):
        self._logger = logging.getLogger("CodeRefactoringAgent")
        self._working_branch = "ReFAct-" + str(uuid.uuid4())

        self._tool_registry = register_tools(project, directory)
        self._project = project
        self._history = [get_system_message(self._tool_registry)]
        self._model = get_llm()

        self._logger.info("Initialized with project %s.", project)

        self._consecutive_error_count = 0

    def _log_agent_message(self, response: ReActOutput):
        # self._logger.info("Plan:\n" + prettify_list(response.plan))
        self._logger.info("Thought: %s", response.thought)
        self._logger.info("Action: %s", response.action)
        self._logger.info("Observation: %s", response.observation)

        if get_settings()["make_plan"] and isinstance(response, PlanReActOutput):
            self._logger.info("Issues:\n %s", prettify_list(response.issues))

    def _add_to_history(self, response: ReActOutput):
        # we don't want to store the full response in the history to keep the context window small
        json_obj = {
            "thought": response.thought,
            "action": response.action,
            "tools_input": response.tools_input,
            "observation": response.observation,
        }
        if get_settings()["make_plan"] and isinstance(response, PlanReActOutput):
            json_obj["issues"] = response.issues
        self._history.append(AIMessage(content=json.dumps(json_obj, indent=4)))

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
        if not get_settings()['clip_context_window']:
            return

        current_token_ct = self._estimate_tokens()
        if current_token_ct <= token_limit:
            self._logger.info("Current token count %s is below limit %s.",
                            current_token_ct,
                            token_limit)
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
        self._logger.info("Clipped message history to %s tokens (limit: %s).",
                          self._estimate_tokens(),
                          token_limit)

    def _append_to_log_file(self, message: BaseMessage):
        # check if the log file exists
        if not os.path.exists(LOG_FILE_DIR):
            os.makedirs(LOG_FILE_DIR)

        log_file = os.path.join(LOG_FILE_DIR, f"{self._working_branch}.json")
        if not os.path.exists(log_file):
            self._logger.info("Creating new log file %s.", log_file)
            with open(log_file, "w", encoding="utf-8") as file:
                log = {
                    'agent_settings': get_settings(),
                    'execution': [],
                    'project': self._project,
                    'llm': self._model.name,
                }
                json.dump(log, file, indent=4)

        # read current log file
        with open(log_file, "r", encoding="utf-8") as file:
            log = json.load(file)

        # append new message
        try:
            log['execution'].append(json.loads(message.content))
        except json.JSONDecodeError:
            log['execution'].append(message.content)

        # write back to log file
        with open(log_file, "w", encoding="utf-8") as file:
            json.dump(log, file, indent=4)

    def _add_to_history_and_log(self, message: BaseMessage):
        """ Add a message to the history and log it to the log file. """
        self._history.append(message)
        self._append_to_log_file(message)

    def _trace_exit(self, num_commits, num_iterations):
        if num_commits >= MAX_NUM_OF_COMMITS:
            self._logger.info(
                "Maximum number of commits reached without calling the 'stop' tool. Terminating."
            )
        elif num_iterations >= HARD_MAX_ITERATIONS:
            self._logger.info(
                "Maximum number of iterations reached. Terminating."
            )

    def build_loaded_prompt(self, history):
        """ Condense the history to a single string. """
        condensed_history = []

        # get all but the very last message
        for i, msg in enumerate(history[1:-1]):
            if isinstance(msg, AIMessage):
                condensed_history.append(f"{i}): AI: {msg.content}")
            elif isinstance(msg, HumanMessage):
                condensed_history.append(f"{i}): Human: {msg.content}")
            elif isinstance(msg, SystemMessage):
                condensed_history.append(f"{i}): System: {msg.content}")
            else:
                condensed_history.append(f"{i}): {msg.content}")

        past_log = "\n - ".join(condensed_history)

        return f"""
        {get_system_message(self._tool_registry)}

        The last step was:
        {history[-1].content if len(history) > 1 else "None"}

        The conversation so far:
        {past_log}
        """

    def _clear_erroneous_history(self):
        if not get_settings()['clear_error_after_n']:
            return
        if self._consecutive_error_count >= MAX_CONSECUTIVE_ERRORS:
            self._consecutive_error_count = 0
            self._history = [get_system_message(self._tool_registry)]

    def _invoke_model(self, history):
        if issubclass(self._model.__class__, BaseChatOpenAI):
            response = self._model.invoke(history)
        else:
            loaded_prompt = self.build_loaded_prompt(history)
            response = self._model.invoke(loaded_prompt)

        response = ensure_langchain_message_format(response)
        return response

    def run(self):
        """ The main execution loop of the agent. """

        system_message = get_system_message(self._tool_registry)
        git_checkout(self._working_branch, create=True)
        self._append_to_log_file(system_message)

        num_commits, num_iterations = 0, 0
        while num_commits < MAX_NUM_OF_COMMITS and num_iterations < HARD_MAX_ITERATIONS:
            num_iterations += 1
            # Note: This loop does not have a termination condition,
            # as the agent should terminate by calling the "stop" tool.
            self._clip_message_history(token_limit=CONTEXT_LIMIT)

            # if the agent seems stuck, we'll try to reset the state
            self._clear_erroneous_history()

            response = self._invoke_model(self._history)
            self._add_to_history_and_log(response)

            try:
                response = parser.parse(response.content)
            except OutputParserException:
                self._consecutive_error_count += 1
                msg = {
                    "error": "Could not parse the response.",
                    "format_instructions": parser.get_format_instructions()
                }
                self._logger.warning(msg)
                next_message = HumanMessage(content=json.dumps(msg, indent=4))
                self._add_to_history_and_log(next_message)
                continue

            self._log_agent_message(response)

            tool = self._get_tool_by_name(response.action)
            if tool is None:
                self._consecutive_error_count += 1
                msg = {
                    "error": f"Tool {response.action} not found.",
                    "available_tools": build_tool_info(self._tool_registry)
                }
                self._logger.warning(msg)
                next_message = HumanMessage(content=json.dumps(msg, indent=4))
                self._add_to_history_and_log(next_message)
                continue

            try:
                tool_result = tool.invoke(response.tools_input)
                msg = {
                    "tool": response.action,
                    "result": tool_result
                }
                self._logger.info(msg)

                next_message = HumanMessage(content=json.dumps(msg, indent=4))
                self._add_to_history_and_log(next_message)

                # increase the count of successful commits
                if response.action == "commit_changes":
                    num_commits += 1
                    if not get_settings()['use_previous_history']:
                        self._history = [system_message]

            except Exception as e: # pylint: disable=broad-exception-caught
                self._consecutive_error_count += 1
                msg = {
                    "tool": response.action,
                    "error": str(e)
                }
                self._logger.warning(msg)
                next_message = HumanMessage(content=json.dumps(msg, indent=4))
                self._add_to_history_and_log(next_message)

            print("========================================")

        self._trace_exit(num_commits, num_iterations)

def ensure_langchain_message_format(message: str | BaseMessage) -> BaseMessage:
    """ Ensure that the message is in the correct format. """

    if isinstance(message, str):
        return AIMessage(content=message)
    return message
