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


def get_tools(sample_project_path: str):

    @tool
    def browse_files():
        """ Get an overview of the source files in the code project. """
        all_files = get_all_code_files(sample_project_path, "src")
        
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

    @tool
    def execute_tests():
        """
        Run test cases to ensure that the refactored code still works.
        Use this tool after each change to the codebase.
        If a test failed, try to understand why it failed and how to avoid it in the future.
        """
        
        bash_cmd = [f'cd {sample_project_path} && npm run test']
        process = subprocess.Popen(bash_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        command, result = process.communicate()

        command = command.decode('utf-8')
        result = result.decode('utf-8')

        # ToDo: Replace with other test runners. This is specific to jest.
        if result.startswith("PASS"):
            LOGGER.info("Tests passed.")
            return "Tests passed. Code may be committed."

        LOGGER.warning(f"Tests failed. Output: {result}")
        return result

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
    def undo_changes(files: list[str]):
        """ Undo the changes to a specific file. """
        for filepath in files:
            fullpath = os.path.join(sample_project_path, filepath)
            git_tools.undo_file(fullpath)
        return "Changes undone."

    @tool
    def overwrite_code(filepath: str, content: str):
        """
        Overwrite the content of a specific file.
        You must provide the full content of the file.
        """
        fullpath = os.path.join(sample_project_path, filepath)
        with open(fullpath, "w") as f:
            f.write(content)

        LOGGER.info(f"File {filepath} overwritten.")
        return "File overwritten."

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
        "execute_tests": execute_tests,
        "commit_changes": commit_changes,
        "undo_changes": undo_changes,
        "overwrite_code": overwrite_code,
        "get_refactoring_techniques": get_refactoring_techniques,
        "stop": stop,
        "ask_buddy": ask_buddy,
        "cyclomatic_complexity_tool": cyclomatic_complexity_tool,
        "get_refactoring_tipps": get_refactoring_tipps
    }
