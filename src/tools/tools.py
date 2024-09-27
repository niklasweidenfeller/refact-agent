import os
from .internals import get_all_code_files
from langchain.tools import BaseTool, StructuredTool, tool
import json
import subprocess
import logging

LOGGER = logging.getLogger("Tools")


PROJECT_ROOT = os.path.abspath(os.path.join(__file__, "..", "..", ".."))

SAMPLE_PROJECT_FOLDER = "sample_project"

@tool
def browse_files():
    """ Get an overview of the source files in the code project. """
    sample_project_path = os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER)
    all_files = get_all_code_files(sample_project_path, "src")
    
    files_w_o_full_path = [os.path.relpath(file, sample_project_path) for file in all_files]    
    
    return "Files: " + ", ".join(files_w_o_full_path)

@tool
def open_file(filepath: str):
    """ Open a specific file to see it's soruce code. """
    fullpath = os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER, filepath)
    with open(fullpath, "r") as f:
        content = f.read()
    return content

@tool
def execute_tests():
    """
    Run test cases to ensure that the refactored code still works.
    Use this tool after each change to the codebase.
    """
    projectdir = os.path.abspath(os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER))

    
    bash_cmd = [f'cd {projectdir} && npm run test']
    process = subprocess.Popen(bash_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    command, result = process.communicate()

    command = command.decode('utf-8')
    result = result.decode('utf-8')

    LOGGER.info(f"Tests executed. Result: {result}")
    return result

@tool
def commit_changes(filepath: str, commit_message: str):
    """
    Commit the changes to the codebase.
    Only commit after running the tests.
    """
    fullpath = os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER, filepath)
    
    check_file_has_changes = subprocess.check_output(["git", "status", "--porcelain", fullpath])
    if check_file_has_changes.decode("utf-8").strip() == "":
        LOGGER.warning(f"Trying to commit unchanged file {filepath}, but no changes found.")
        return "No changes to commit."

    subprocess.check_output(["git", "add", fullpath])
    subprocess.check_output(["git", "commit", "-m", f"ReFAct: {commit_message}"])

    LOGGER.info(f"Changes to {filepath} committed.")
    return "Changes committed."

@tool
def undo_changes(filepath: str):
    """ Undo the changes to a specific file. """
    fullpath = os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER, filepath)
    subprocess.check_output(["git", "checkout", fullpath])

    return "Changes undone."

@tool
def overwrite_code(filepath: str, content: str):
    """ Overwrite the content of a specific file. """
    fullpath = os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER, filepath)
    with open(fullpath, "w") as f:
        f.write(content)

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
    exit(0)
