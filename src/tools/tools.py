import os
import subprocess
import logging
import shutil

from langchain.tools import tool
from langchain_core.messages import HumanMessage
from typing import List, Dict

from .internals import get_all_code_files
from llm import get_gpt_llm

import lizard

LOGGER = logging.getLogger("Tools")

from . import git_tools


def get_tools(sample_project_path: str, source_code_dir: str) -> dict:

    @tool
    def browse_files() -> str:
        """ Get an overview of the source files in the code project. """
        all_files = get_all_code_files(sample_project_path, source_code_dir)
        
        files_w_o_full_path = [os.path.relpath(file, sample_project_path) for file in all_files]    
        
        return "Files: " + ", ".join(files_w_o_full_path)

    @tool
    def open_file(filepath: str) -> str:
        """ Open a specific file to see it's soruce code. """
        LOGGER.info(f"Opening file {filepath}")
        filepath = filepath.lstrip("/")
        fullpath = os.path.join(sample_project_path, filepath)
        if not os.path.exists(fullpath):
            return f"File {filepath} does not exist."
        with open(fullpath, "r") as f:
            content = f.read()
        return content

    def node_js_test_runner() -> tuple[bool, str]:
        """ Run the test cases for a Node.js project. """
        bash_cmd = [f'cd {sample_project_path} && npm run test']
        process = subprocess.Popen(bash_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        command, result = process.communicate()

        command = command.decode('utf-8')
        result = result.decode('utf-8')

        # ToDo: Replace with other test runners. This is specific to jest.
        if result.startswith("PASS"):
            LOGGER.info("Tests passed.")
            return True, "Tests passed. Code may be committed."

        LOGGER.warning(f"Tests failed. Output: {result}")
        return False, result

    def python_test_runner() -> tuple[bool, str]:
        """ Run the test cases for a Python project. """
        bash_cmd = [f"cd {sample_project_path} && pytest | sed -e 's/\x1b\[[0-9;]*m//g'"]
        process = subprocess.Popen(bash_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        command, _ = process.communicate()
        command = command.decode("utf-8")

        lines = command.splitlines()
        lines = [line for line in lines if line]
        
        result_line = lines[-1]
        erroneous_lines = [line for line in lines if line.startswith("FAILED") or line.startswith("ERROR")]

        if len(erroneous_lines) > 0:
            return False, result_line + "\n".join(erroneous_lines)
        return True, "Tests passed. Code may be committed."

    def java_test_runner() -> tuple[bool, str]:
        """ Compile and run the test cases for a Java project. """
        def parse_mvn_output(output_string: str) -> tuple[bool, str]:
            parsed_command = output_string.split("\n")

            if any("[INFO] BUILD SUCCESS" in s for s in parsed_command):
                return True, "[INFO] SUCCESS"

            error_lines = [s for s in parsed_command if s.startswith("[ERROR]")]
            if len(error_lines) > 0:
                return False, "\n".join(error_lines)
            return False, "[ERROR] FAILURE"

        # clean the build directory
        build_dir = os.path.join(sample_project_path, "target")
        try:
            shutil.rmtree(build_dir)
        except OSError as e:
            # the target directory might not exist yet
            LOGGER.warning(f"Error: {e.filename} - {e.strerror}.")

        # compile the code
        bash_cmd = [f'cd {sample_project_path} && mvn compile']
        process = subprocess.Popen(bash_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        command, _ = process.communicate()
        compilation_output = command.decode("utf-8")

        # verify the compilation        
        compilation_success, detail = parse_mvn_output(compilation_output)
        if not compilation_success:
            return False, f"Compilation Error: {detail}"

        # exec unit tests
        bash_cmd = [f'cd {sample_project_path} && mvn test']
        process = subprocess.Popen(bash_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        command, _ = process.communicate()
        test_output = command.decode("utf-8")
        test_success, detail = parse_mvn_output(test_output)
        if not test_success:
            return False, detail

        # comilation and test successfull
        return True, "[INFO] COMPILATION & TEST SUCCESS"

    @tool
    def commit_changes(files: list[str], commit_message: str) -> str:
        """
        Commit the changes to the codebase.
        Only commit after running the tests.
        Please make the commit message as descriptive as possible.
        """

        for filepath in files:
            fullpath = os.path.join(sample_project_path, filepath)

            if not git_tools.has_file_changes(fullpath):
                LOGGER.warning(f"Trying to commit unchanged file {filepath}, but no changes found.")
                return "No changes to commit."
            git_tools.stage_file(fullpath)

        git_tools.commit(f"[ReFAct]: {commit_message}")
        LOGGER.info(f"Changes to {filepath} committed.")
        return "Changes committed."

    def _undo_changes(files: list[str]) -> str:
        """ Undo the changes to a specific file. """
        for filepath in files:
            fullpath = os.path.join(sample_project_path, filepath)
            git_tools.undo_file(fullpath)
        return "Changes have been reverted."

    def _execute_tests() -> tuple[bool, str]:
        """
        Run test cases to ensure that the refactored code still works.
        Use this tool after each change to the codebase.
        If a test failed, try to understand why it failed and how to avoid it in the future.
        """
        all_code_files = get_all_code_files(sample_project_path, source_code_dir)
        if any(file.endswith(".py") for file in all_code_files):
            return python_test_runner()
        if any(file.endswith(".java") for file in all_code_files):
            return java_test_runner()
        return node_js_test_runner()

    def _write_to_file(filepath: str, content: str) -> None:
        """ Write the content to a specific file. """
        filepath = filepath.lstrip("/")
        if "\"\.\"" in content:
            content = content.replace("\"\.\"", "\"\\\\.\"")
        fullpath = os.path.join(sample_project_path, filepath)
        with open(fullpath, "w") as f:
            f.write(content)

    def _pass_tests_or_undo_changes(files: list[str]) -> str:
        success, text = _execute_tests()
        if success:
            msg = "Tests passed. Please commit your changes."
            LOGGER.info(msg)
            return msg
        undo_result = _undo_changes(files)
        msg = f"Refactoring failed. {undo_result} Output: {text}."
        LOGGER.warning(msg)
        return msg

    @tool
    def overwrite_file(filepath: str, content: str) -> str:
        """
        Overwrite the content of a specific file.

        ALWAYS RESPOND WITH THE ENTIRE FILE CONTENT, NOT JUST SNIPPETS.
        """
        _write_to_file(filepath, content)
        LOGGER.info(f"File {filepath} overwritten. Beginning test execution.")
        return _pass_tests_or_undo_changes([filepath])

    without_whitespace = lambda s: s.replace(" ", "").replace("\n", "")

    @tool
    def overwrite_single_method(filepath: str, method_name: str, refactored_method: str) -> str:
        """
        Overwrite the content of a specific method in a file. Use this tool, if you're only changing a specific method.
        You must provide the full updated method, including the method signature.
        This tool is useful, if the file is very large and you only want to change a specific method.
        (Includes splitting the method into multiple methods.)

        After you have executed this tool and commited your changes, you MUST check the code complexity again!
        """

        filepath = filepath.lstrip("/")
        fullpath = os.path.join(sample_project_path, filepath)

        with open(fullpath, "r") as f:
            content_lines_from_disk = f.readlines()

        # determine indentation level in the original file
        method_start = refactored_method.split(f"{method_name}(")[0] + method_name
        original_start_line = next(
            (line for line in content_lines_from_disk if method_start in line),
            None
        )
        if not original_start_line:
            msg = f"Method {method_name} not found in file {filepath}."
            LOGGER.warning(msg)
            return msg

        # we need to update the start and end line numbers
        start = content_lines_from_disk.index(original_start_line)

        is_curly_brace_language = any(filepath.endswith(ext) for ext in [".java", ".c", ".cpp", ".h", ".hpp", ".js", ".ts"])
        if not is_curly_brace_language:
            msg = "Language not supported. Please use the overwrite_file tool."
            LOGGER.warning(msg)
            return msg

        # find the end of the method by counting curly braces
        end = None
        open_braces = 0
        for i, line in enumerate(content_lines_from_disk[start:]):
            open_braces += line.count("{")
            if open_braces > 0:
                open_braces -= line.count("}")
                if open_braces == 0:
                    end = start + i + 1
                    break

        if end is None:
            msg = f"Could not determine the end of the method {method_name} in file {filepath}."
            LOGGER.warning(msg)
            return msg

        original_start_until_params = original_start_line.split("(")[0]
        indentation = original_start_until_params.split(method_start)[0]

        tmp = []
        for line in refactored_method.split("\n"):
            if line.strip() == "":
                tmp.append("")
            else:
                tmp.append(indentation + line)
        refactored_method = "\n".join(tmp)

        # debugging: get entire old method
        old_method = "".join(content_lines_from_disk[start:end])
        LOGGER.info(f"Old method:\n{old_method}\nNew method:\n{refactored_method}")

        # merge the new content into the file
        old_until_start = "".join(content_lines_from_disk[:start])
        old_after_end = "".join(content_lines_from_disk[end+1:])
        final_content_to_write = old_until_start + refactored_method + "\n" + old_after_end

        has_changed = without_whitespace("".join(content_lines_from_disk)) != without_whitespace(final_content_to_write)
        if not has_changed:
            msg = "The new code is exactly the same as the old code! Try again!"
            LOGGER.warning(msg)
            return msg

        _write_to_file(filepath, final_content_to_write)
        LOGGER.info(f"Method {method_name} in file {filepath} overwritten. Beginning test execution.")
        return _pass_tests_or_undo_changes([filepath])

    @tool
    def get_refactoring_techniques() -> str:
        """ Get a list of commonly used refactoring steps. """
        with open("catalog.txt", "r") as f:
            lines = f.readlines()
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line]
        return "Refactoring techniques: " + ", ".join(lines)

    @tool
    def stop(changes_summary: str) -> None:
        """ Call this tool when you see no further refactoring Opportunities. """
        LOGGER.info(f"Refactoring finished. Summary: {changes_summary}")
        target_branch = "main"
        current_branch = git_tools.get_current_branch()
        LOGGER.info(f"Stopping refactoring. Merging from {current_branch} into {target_branch}.")
        git_tools.merge(git_tools.get_current_branch(), target_branch, squash=True, message=changes_summary)
        exit(0)

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
        LOGGER.info(f"Buddy feedback: {llm_response.content}")
        return llm_response.content

    @tool
    def cyclomatic_complexity_tool(top_n: int = 10) -> list[dict] | str:
        """
        In the current directory, get the top_n functions with the highest cyclomatic complexity.
        Usually, a cyclomatic complexity of 15 or higher is considered bad code.
        """

        lizard_result_file_list = list(lizard.analyze([sample_project_path]))
        lizard_result_functions = []
        for file in lizard_result_file_list:
            lizard_result_functions.extend(x.__dict__ for x in file.function_list)

        shorten_file_path = lambda file_path: file_path.split(str(sample_project_path))[1]
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
            return "There are no functions with a cyclomatic complexity of 15 or higher in the codebase."

        all_functions = sorted(all_functions, key=lambda x: x['cyclomatic_complexity'], reverse=True)
        return all_functions[:top_n]

    @tool
    def get_refactoring_tipps() -> str:
        """
        Get a list of commonly used refactoring steps.
        Use this list when you are unsure about the next refactoring step,
        or when you think you are mostly done with the refactoring.
        """
        from const import REFACTORINGS_FOWLER
        return REFACTORINGS_FOWLER

    return {
        "browse_files": browse_files,
        "open_file": open_file,
        # "execute_tests": execute_tests,
        "commit_changes": commit_changes,
        # "undo_changes": undo_changes,
        "overwrite_file": overwrite_file,
        "overwrite_single_method": overwrite_single_method,
        "get_refactoring_techniques": get_refactoring_techniques,
        "stop": stop,
        "ask_buddy": ask_buddy,
        "cyclomatic_complexity_tool": cyclomatic_complexity_tool,
        "get_refactoring_tipps": get_refactoring_tipps
    }
