import os
import subprocess
import logging

from langchain.tools import tool
from langchain_core.messages import HumanMessage
from typing import List, Dict

from .internals import get_all_code_files
from llm import get_gpt_llm


LOGGER = logging.getLogger("Tools")

from . import git_tools

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
    If a test failed, try to understand why it failed and how to avoid it in the future.
    """
    projectdir = os.path.abspath(os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER))

    
    bash_cmd = [f'cd {projectdir} && npm run test']
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
        fullpath = os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER, filepath)

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
        fullpath = os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER, filepath)
        git_tools.undo_file(fullpath)
    return "Changes undone."

@tool
def overwrite_code(filepath: str, content: str):
    """
    Overwrite the content of a specific file.
    You must provide the full content of the file.
    """
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
    git_tools.merge("main", f"ReFAct: {changes_summary}", squash=True)
    LOGGER.info(f"Refactoring finished. Summary: {changes_summary}")
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
def get_refactoring_tipps():
    """
    Get a list of commonly used refactoring steps.
    Use this list when you are unsure about the next refactoring step,
    or when you think you are mostly done with the refactoring.
    """
        
    REFACTORINGS_FOWLER = """
    Change...
        ... Function Declaration
        ... Reference to Value
        ... Value to Reference
    Collapse Hierarchy
    Combine...
        ... Functions into Class
        ... Functions into Transform
    Consolidate Conditional Expression
    Decompose Conditional
    Encapsulate...
        ... Collection
        ... Record
        ... Variable
    Extract...
        ... Class
        ... Function
        ... Superclass
        ... Variable
    Hide Delegate
    Inline...
        ... Class
        ... Function
        ... Variable
    Introduce...
        ... Assertion
        ... Parameter Object
        ... Special Case
    Move...
        ... Field
        ... Function
        ... Statements into Function
        ... Statements to Callers
    Parameterize Function
    Preserve Whole Object
    Pull Up...
        ... Constructor Body
        ... Field
        ... Method
    Push Down...
        ... Field
        ... Method
    Remove...
        ... Dead Code
        ... Flag Argument
        ... Middle Man
        ... Setting Method
        ... Subclass
        ... Field
        ... Variable
    Replace...
        ... Command with Function
        ... Conditional with Polymorphism
        ... Constructor with Factory Method
        ... Control Flag with Break
        ... Derived Variable with Query
        ... Error Code with Exception
        ... Exception with Precheck
        ... Function with Command
        ... Inline Code with Function Call
        ... Loop with Pipeline
        ... Magic Literal
        ... Nested Conditional with Guard Clauses
        ... Parameter with Query
        ... Primitive with Object
        ... Query with Parameter
        ... Subclass with Delegate
        ... Superclass with Delegate
        ... Temp with Query
        ... Type Code with Subclasses
    Return Modified Value
    Separate Query from Modifier
    Slide Statements
    Split
        ... Loop
        ... Phase
        ... Variable
    Substitute Algorithm
    """

    return REFACTORINGS_FOWLER