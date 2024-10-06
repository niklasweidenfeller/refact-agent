""" Contains all LangChain tools for the ReAct agent. """

import os
import sys
import logging

from typing import List, Dict

import lizard
from langchain.tools import tool
from langchain_core.messages import HumanMessage

from const import REFACTORINGS_FOWLER
from llm import get_gpt_llm

from . import git_tools
from .internals import get_all_code_files
from . import test_runners

LOGGER = logging.getLogger("Tools")
CURLY_BRACE_ENDINGS = [".java", ".c", ".cpp", ".h", ".hpp", ".js", ".ts"]

def warning(msg: str) -> str:
    """ Log a warning and return a message. """
    LOGGER.warning(msg)
    return msg

class ToolFactory:
    """ Class to hold all LangChain tools for the ReAct agent. """

    def __init__(self, sample_project_path: str, source_code_dir: str):
        self._sample_project_path = sample_project_path
        self._source_code_dir = source_code_dir

    def get_browse_files_tool(self) -> callable:
        """ Get the browse_files tool. """

        @tool
        def browse_files() -> str:
            """ Get an overview of the source files in the code project. """
            all_files = get_all_code_files(self._sample_project_path, self._source_code_dir)
            files_w_o_full_path = [
                os.path.relpath(file, self._sample_project_path) for file in all_files
            ]
            return "Files: " + ", ".join(files_w_o_full_path)

        return browse_files

    def get_open_file_tool(self) -> callable:
        """ Get the open_file tool. """

        @tool
        def open_file(filepath: str) -> str:
            """ Open a specific file to see it's soruce code. """
            LOGGER.info("Opening file %s.", filepath)
            filepath = filepath.lstrip("/")
            fullpath = os.path.join(self._sample_project_path, filepath)
            if not os.path.exists(fullpath):
                return f"File {filepath} does not exist."
            with open(fullpath, "r", encoding="utf-8") as f:
                content = f.read()
            return content

        return open_file

    def get_commit_changes_tool(self) -> callable:
        """ Get the commit_changes tool. """

        @tool
        def commit_changes(files: list[str], commit_message: str) -> str:
            """
            Commit the changes to the codebase.
            Only commit after running the tests.
            Please make the commit message as descriptive as possible.
            """

            for filepath in files:
                fullpath = self._get_full_path(filepath)

                if not git_tools.has_file_changes(fullpath):
                    return warning(f"No changes to commit for file {filepath}.")
                git_tools.stage_file(fullpath)

            git_tools.commit(f"[ReFAct]: {commit_message}")
            LOGGER.info("Changes to files %s committed.", ", ".join(files))
            return "Changes committed."

        return commit_changes

    def get_overwrite_file_tool(self) -> callable:
        """ Get the overwrite_file tool. """

        @tool
        def overwrite_file(filepath: str, content: str) -> str:
            """
            Overwrite the content of a specific file.

            ALWAYS RESPOND WITH THE ENTIRE FILE CONTENT, NOT JUST SNIPPETS.
            """
            write_to_file(self._get_full_path(filepath), content)
            LOGGER.info("File %s overwritten. Beginning test execution.", filepath)
            return self._pass_tests_or_undo_changes([filepath])

        return overwrite_file

    def get_overwrite_single_method_tool(self) -> callable:
        """ Get the overwrite_single_method tool. """

        @tool
        def overwrite_single_method(filepath: str, method_name: str, refactored_method: str) -> str:
            """
            Overwrite the content of a specific method in a file. Use this tool, if you're only
            changing a specific method.
            You must provide the full updated method, including the method signature.
            This tool is useful, if the file is very large and you only want to change a specific
            method.
            (Includes splitting the method into multiple methods.)
            
            CURRENTLY WORKS ONLY FOR CURLY BRACE LANGUAGES (Java, C, C++, JavaScript, TypeScript).

            After you have executed this tool and commited your changes, you MUST check the code
            complexity again!
            """

            filepath = filepath.lstrip("/")
            if not is_curly_brace_language(filepath):
                return warning(
                    "Language not supported. Please use the overwrite_file tool."
                )

            with open(self._get_full_path(filepath), "r", encoding="utf-8") as f:
                content_lines_from_disk = f.readlines()

            # determine indentation level in the original file
            method_start = refactored_method.split(f"{method_name}(")[0] + method_name
            original_start_line = next(
                (line for line in content_lines_from_disk if method_start in line),
                None
            )

            if not original_start_line:
                return warning(f"Method {method_name} not found in file {filepath}.")

            # we need to update the start and end line numbers
            start = content_lines_from_disk.index(original_start_line)

            # find the end of the method by counting curly braces
            length = determine_length_of_curly_brace_block(content_lines_from_disk[start:])
            if not length:
                return warning(
                    f"Could not determine the end of the method {method_name} in file {filepath}."
                )
            end = start + length

            indentation = diff_leading_whitespace(original_start_line, method_start)
            refactored_method = indent_code_block(refactored_method, indentation)

            # merge the new content into the file
            old_until_start = "".join(content_lines_from_disk[:start])
            old_after_end = "".join(content_lines_from_disk[end+1:])
            final_content_to_write = old_until_start + refactored_method + "\n" + old_after_end

            if not has_content_changed("".join(content_lines_from_disk), final_content_to_write):
                return warning("The new code is exactly the same as the old code! Try again!")

            write_to_file(self._get_full_path(filepath), final_content_to_write)
            LOGGER.info("Method %s in file %s overwritten. Beginning test execution.",
                        method_name,
                        filepath)
            return self._pass_tests_or_undo_changes([filepath])

        return overwrite_single_method

    def get_refactoring_techniques_tool(self) -> callable:
        """ Get the get_refactoring_techniques tool. """

        @tool
        def get_refactoring_techniques() -> str:
            """ Get a list of commonly used refactoring steps. """
            with open("catalog.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
            lines = [line.strip() for line in lines]
            lines = [line for line in lines if line]
            return "Refactoring techniques: " + ", ".join(lines)

        return get_refactoring_techniques

    def get_stop_tool(self) -> callable:
        """ Get the stop tool. """

        @tool
        def stop(changes_summary: str) -> None:
            """ Call this tool when you see no further refactoring Opportunities. """
            LOGGER.info("Refactoring finished. Summary: %s", changes_summary)
            target_branch = "main"
            current_branch = git_tools.get_current_branch()
            LOGGER.info("Stopping refactoring. Merging from %s into %s.",
                        current_branch,
                        target_branch)
            git_tools.merge(current_branch, target_branch, squash=True)
            git_tools.commit(f"[ReFAct]: {changes_summary}")
            sys.exit(0)

        return stop

    def get_ask_buddy_tool(self) -> callable:
        """ Get the ask_buddy tool. """
        @tool
        def ask_buddy(code: str) -> str | List[str | Dict]:
            """
            Ask your buddy for feedback on the current code.
            A second pair of eyes can help you spot issues you might have missed
            or provide you with new ideas for refactoring.
            """

            LOGGER.info("Requesting buddy feedback.")
            llm = get_gpt_llm()

            input_message = HumanMessage(
                content=f"""
                Please review the following code.
                Which areas could be improved?
                What should I look out for when refactoring?

                {code}
                """
            )

            llm_response = llm.invoke([input_message])
            LOGGER.info("Buddy feedback: %s", llm_response.content)
            return llm_response.content
        return ask_buddy

    def get_cyclomatic_complexity_tool(self):
        """ Get the cyclomatic_complexity_tool. """
        @tool
        def cyclomatic_complexity_tool(top_n: int = 10) -> list[dict] | str:
            """
            In the current directory, get the top_n functions with the highest cyclomatic
            complexity.
            Usually, a cyclomatic complexity of 15 or higher is considered bad code.
            """

            lizard_result_file_list = list(lizard.analyze([
                os.path.join(self._sample_project_path,
                             self._source_code_dir)
            ]))
            lizard_result_functions = []
            for file in lizard_result_file_list:
                lizard_result_functions.extend(x.__dict__ for x in file.function_list)

            def shorten_file_path(file_path: str) -> str:
                return file_path.split(str(self._sample_project_path))[1]

            all_functions = [{
                    'nloc': x['nloc'],
                    'cyclomatic_complexity': x['cyclomatic_complexity'],
                    'parameter_count': len(x['full_parameters']),
                    'function_name': x['name'],
                    'filename': shorten_file_path(x['filename']),
                    'start_line': x['start_line'],
                    'end_line': x['end_line']
                } for x in lizard_result_functions]

            # get the functions with complexity >= 15
            all_functions = [x for x in all_functions if x['cyclomatic_complexity'] >= 15]
            if len(all_functions) == 0:
                return "No functions with a cyclomatic complexity of >= 15 in the codebase."

            all_functions = sorted(all_functions,
                                key=lambda x: x['cyclomatic_complexity'],
                                reverse=True)
            return all_functions[:top_n]

        return cyclomatic_complexity_tool

    def get_refactoring_tipps_tool(self) -> callable:
        """ Get the get_refactoring_tipps tool. """

        @tool
        def get_refactoring_tipps() -> str:
            """
            Get a list of commonly used refactoring steps.
            Use this list when you are unsure about the next refactoring step,
            or when you think you are mostly done with the refactoring.
            """
            return REFACTORINGS_FOWLER

        return get_refactoring_tipps

    def _execute_tests(self) -> tuple[bool, str]:
        """
        Run test cases to ensure that the refactored code still works.
        Use this tool after each change to the codebase.
        If a test failed, try to understand why it failed and how to avoid it in the future.
        """
        all_code_files = get_all_code_files(self._sample_project_path, self._source_code_dir)
        if any(file.endswith(".py") for file in all_code_files):
            return test_runners.python_test_runner(self._sample_project_path)
        if any(file.endswith(".java") for file in all_code_files):
            return test_runners.java_test_runner(self._sample_project_path)
        return test_runners.node_js_test_runner(self._sample_project_path)

    def _pass_tests_or_undo_changes(self, files: list[str]) -> str:
        success, text = self._execute_tests()
        if success:
            msg = "Tests passed. Please commit your changes."
            LOGGER.info(msg)
            return msg
        undo_result = undo_changes(self._sample_project_path, files)
        return warning(f"Refactoring failed. {undo_result} Output: {text}.")

    def _get_full_path(self, filepath: str) -> str:
        filepath = filepath.lstrip("/")
        return os.path.join(self._sample_project_path, filepath)

def undo_changes(project_path, files: list[str]) -> str:
    """ Undo the changes to a specific file. """
    for filepath in files:
        fullpath = os.path.join(project_path, filepath)
        git_tools.undo_file(fullpath)
    return "Changes have been reverted."

def write_to_file(path: str, content: str) -> None:
    """ Write the content to a specific file. """
    if r'"\."' in content:
        content = content.replace(r'"\."', r'"\\."')
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def without_whitespace(s: str) -> str:
    """ Remove all whitespace characters from a string. """

    return s.replace(" ", "").replace("\n", "")

def is_curly_brace_language(filepath: str) -> bool:
    """ Check if the file is a curly brace language. """
    return any(filepath.endswith(ext) for ext in CURLY_BRACE_ENDINGS)

def determine_length_of_curly_brace_block(lines: List[str]) -> int | None:
    """ Determine the end of a curly brace block. """
    open_braces = 0
    for i, line in enumerate(lines):
        open_braces += line.count("{")
        if open_braces > 0:
            open_braces -= line.count("}")
            if open_braces == 0:
                return i + 1
    return None

def diff_leading_whitespace(old: str, new: str) -> str:
    """ Determine the leading whitespace in the new string. """

    original_start_until_params = old.split("(")[0]
    indentation = original_start_until_params.split(new)[0]
    return indentation

def indent_code_block(code_block: str, indentation: str) -> str:
    """ Indent a code block by a specific indentation. """

    tmp = []
    for line in code_block.split("\n"):
        if line.strip() == "":
            tmp.append("")
        else:
            tmp.append(indentation + line)
    return "\n".join(tmp)

def has_content_changed(old_content: str, new_content: str) -> bool:
    """ Check if the content has changed. """
    old_wo_whitespace = without_whitespace(old_content)
    new_wo_whitespace = without_whitespace(new_content)
    return old_wo_whitespace != new_wo_whitespace
