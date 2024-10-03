import os
import subprocess
import logging

from langchain.tools import tool
from langchain_core.messages import HumanMessage
from typing import List, Dict

from .internals import get_all_code_files
from llm import get_gpt_llm

import lizard

LOGGER = logging.getLogger("Tools")

from . import git_tools


def get_tools(sample_project_path: str, source_code_dir: str):

    @tool
    def browse_files():
        """ Get an overview of the source files in the code project. """
        all_files = get_all_code_files(sample_project_path, source_code_dir)
        
        files_w_o_full_path = [os.path.relpath(file, sample_project_path) for file in all_files]    
        
        return "Files: " + ", ".join(files_w_o_full_path)

    @tool
    def open_file(filepath: str):
        """ Open a specific file to see it's soruce code. """
        LOGGER.info(f"Opening file {filepath}")
        fullpath = os.path.join(sample_project_path, filepath)
        with open(fullpath, "r") as f:
            content = f.read()
        return content

    def node_js_test_runner():
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

    def python_test_runner():
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

    def java_test_runner():
        def parse_mvn_output(output_string):
            parsed_command = output_string.split("\n")

            if any("[INFO] BUILD SUCCESS" in s for s in parsed_command):
                return True, "[INFO] SUCCESS"

            error_lines = [s for s in parsed_command if s.startswith("[ERROR]")]
            if len(error_lines) > 0:
                return False, "\n".join(error_lines)
            return False, "[ERROR] FAILURE"

        # clean the build directory
        
        bash_cmd = [f'cd {sample_project_path} && rf -rf target']
        try:
            subprocess.run(bash_cmd)
        except:
            # the target directory might not exist yet
            LOGGER.info("Target directory not found. Skipping deletion.")
            pass

        # compile the code
        bash_cmd = [f'cd {sample_project_path} && mvn compile']
        process = subprocess.Popen(bash_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        command, _ = process.communicate()
        compilation_output = command.decode("utf-8")

        # verify the compilation        
        compilation_success, detail = parse_mvn_output(compilation_output)
        if not compilation_success:
            return False, detail

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
    def commit_changes(files: list[str], commit_message: str):
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

    @tool
    def overwrite_code(filepath: str, content: str):
        """
        Overwrite the content of a specific file.
        You must provide the full content of the file.
        """

        def execute_tests():
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

        def undo_changes(files: list[str]):
            """ Undo the changes to a specific file. """
            for filepath in files:
                fullpath = os.path.join(sample_project_path, filepath)
                git_tools.undo_file(fullpath)
            return "Changes have been reverted."

        
        fullpath = os.path.join(sample_project_path, filepath)
        with open(fullpath, "w") as f:
            f.write(content)

        LOGGER.info(f"File {filepath} overwritten.")

        success, text = execute_tests()
        if success:
            msg = "Tests passed. Please commit your changes."
            LOGGER.info(msg)
            return msg

        undo_result = undo_changes([filepath])
        msg = f"Refactoring failed. {undo_result} Output: {text}."
        LOGGER.warning(msg)
        return msg

    @tool
    def get_refactoring_techniques():
        """ Get a list of commonly used refactoring steps. """
        with open("catalog.txt", "r") as f:
            lines = f.readlines()
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line]
        return "Refactoring techniques: " + ", ".join(lines)

    @tool
    def stop(changes_summary: str):
        """ Call this tool when you see no further refactoring Opportunities. """
        LOGGER.info(f"Refactoring finished. Summary: {changes_summary}")
        target_branch = "main"
        current_branch = git_tools.get_current_branch()
        LOGGER.info(f"Stopping refactoring. Merging from {current_branch} into {target_branch}.")
        git_tools.merge(git_tools.get_current_branch(), target_branch, squash=True)
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
    def cyclomatic_complexity_tool(filepath: str) -> list[dict]:
        """
        Get the cyclomatic complexity information for all functions in a specific file.
        Cyclomatic complexity is a software metric used to indicate the complexity of a program.
        Functions with high cyclomatic complexity are good candidates for refactoring.
        """

        fullpath = os.path.join(sample_project_path, filepath)
        lizard_result_functions = [x.__dict__ for x in lizard.analyze_file(fullpath).function_list]
        
        shorten_file_path = lambda file_path: file_path.split(str(sample_project_path))[1]
        all_functions = [{
                'nloc': x['nloc'],
                'cyclomatic_complexity': x['cyclomatic_complexity'],
                'parameter_count': len(x['full_parameters']),
                'function_name': x['name'],
                'filename': shorten_file_path(x['filename'])
            } for x in lizard_result_functions]
        return sorted(all_functions, key=lambda x: x['cyclomatic_complexity'], reverse=True)

    @tool
    def get_refactoring_tipps():
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
        "overwrite_code": overwrite_code,
        "get_refactoring_techniques": get_refactoring_techniques,
        "stop": stop,
        "ask_buddy": ask_buddy,
        "cyclomatic_complexity_tool": cyclomatic_complexity_tool,
        "get_refactoring_tipps": get_refactoring_tipps
    }
