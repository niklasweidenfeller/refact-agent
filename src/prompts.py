import os, json, logging

from langchain_core.messages import SystemMessage
from langchain.output_parsers import PydanticOutputParser

from pydantic import BaseModel, Field

from tools import tools

tool_registry = [
    tools.browse_files,
    tools.open_file,
    tools.execute_tests,
    tools.overwrite_code,
    tools.commit_changes,
    tools.undo_changes,
    tools.stop,
    tools.get_refactoring_tipps,
]

LOGGER = logging.getLogger("Tools")


PROJECT_ROOT = os.path.abspath(os.path.join(__file__, "..", "..", ".."))

SAMPLE_PROJECT_FOLDER = "sample_project"


class ReActOutput(BaseModel):
    thought: str = Field(description="Your current thought.")
    action: str = Field(description="The tool to use.")
    tools_input: dict = Field(description="The input to the action.")
    observation: str = Field(description="Your observation.")
    # plan: list[str] = Field(description="Your long-term plan. Should be a list of steps. Consider, how you want the code to look like in the future.")
    issues: list[str] = Field(
        description="""
        A very precise list of all issues and code smells that you can find in the codebase.
        Pay attention for anti-patterns, code smells, and other issues. Also pay attention to the code quality and testability.
        Each issue should be broken down as much as possible.
        Try to understand why the issue is there and what the best way to address it is.
        """
    )

parser = PydanticOutputParser(pydantic_object=ReActOutput)

def get_tool_by_name(name):
    for tool in tool_registry:
        if tool.name == name:
            return tool
    return None

def build_tool_info():
    tools_info = []
    for tool in tool_registry:
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
            "args": tool.args
        })
    return json.dumps(tools_info, indent=4)



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


def get_system_message():

    tool_info = build_tool_info()
    format_instructions = parser.get_format_instructions()

    msg = f"""
    You are a professional software developer.
    Your job is to refactor the existing codebases.
    You work in a loop of thought, action, and observation.

    Your task is to make a precise list of issues in the codebase.
    You can update this list as you go.
    For each issue, you will use a refactoring technique to address it.
    You can use a variety of tools to assist you.
    Only make very incremental changes to the codebase, which touch as few lines as possible.
    If the changes seem overwhelming, start with the most obvious ones, such as renaming variables or functions, inverting conditions, or extracting functions.
    After each issue, run the tests to ensure that the code still works, and commit the changes to the codebase.

    If a test failed, come up with a new plan to address the issue.

    Then, proceed with the next issue.
    You can also revisit files you have already worked on.

    The following tools are available:
    {tool_info}

    Respond with the tool you would like to use.
    You don't have to worry about writing tests, as they are already provided.

    AFTER EACH CHANGE, RUN THE TESTS TO ENSURE THAT THE CODE STILL WORKS.
    IF THE CODE WORKS, COMMIT THE CHANGES TO THE CODEBASE.
    IF THE CODE DOES NOT WORK, REVERT THE CHANGES AND TRY AGAIN.
    FOCUS ON ONE ISSUE AT A TIME. BREAK EVERYTHING DOWN INTO SMALL STEPS.

    {format_instructions}
    """

    return SystemMessage(content=msg)
