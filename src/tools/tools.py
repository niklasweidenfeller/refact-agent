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
        return "Tests passed."

    LOGGER.warning(f"Tests failed. Output: {result}")
    return result

@tool
def commit_changes(files: list[str], commit_message: str):
    """
    Commit the changes to the codebase.
    Only commit after running the tests.
    """

    for filepath in files:
        fullpath = os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER, filepath)

        check_file_has_changes = subprocess.check_output(["git", "status", "--porcelain", fullpath])
        if check_file_has_changes.decode("utf-8").strip() == "":
            LOGGER.warning(f"Trying to commit unchanged file {filepath}, but no changes found.")
            return "No changes to commit."

        subprocess.check_output(["git", "add", fullpath])
    subprocess.check_output(["git", "commit", "-m", f"[ReFAct]: {commit_message}"])

    LOGGER.info(f"Changes to {filepath} committed.")
    return "Changes committed."

@tool
def undo_changes(files: list[str]):
    """ Undo the changes to a specific file. """
    for filepath in files:
        fullpath = os.path.join(PROJECT_ROOT, SAMPLE_PROJECT_FOLDER, filepath)
        subprocess.check_output(["git", "checkout", fullpath])

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
    LOGGER.info(f"Refactoring finished. Summary: {changes_summary}")
    exit(0)


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