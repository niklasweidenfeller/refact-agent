""" Contains everything related to the ReAct agent's System Prompt. """

import json
import logging
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage
from langchain.output_parsers import PydanticOutputParser

from .config import get_settings


LOGGER = logging.getLogger("Tools")


class ReActOutput(BaseModel):
    """ Pydantic model for the ReAct agent's output. """

    thought: str = Field(description="Your current thought.")
    action: str = Field(description="The tool to use.")
    tools_input: dict = Field(description="The input to the tool.")
    observation: str = Field(description="Your observation.")


class PlanReActOutput(ReActOutput):
    """
    Pydantic model which adds a plan to ReAct.
    Used for PlanReAct, which is a version of ReAct
    where the agent makes a plan before taking action.
    """

    issues: list[str] = Field(
        description=f"""
        A list of all issues and code smells that you can find in the codebase. Pay attention for anti-patterns,
        code smells, and more. Also pay attention to the code quality and testability.
        {"Each issue should be broken down, when possible." if get_settings()["make_incremental_changes"] else ""}
        Explain why the issue is there and what the best way to address it is.
        {"YOU MUST UPDATE THIS LIST AS YOU GO." if get_settings()["dynamic_plan"] else ""}
        """
    )

parser = PydanticOutputParser(
    pydantic_object=PlanReActOutput if get_settings()["make_plan"] else ReActOutput
)

def build_tool_info(tool_registry):
    """
    Serialize the tool registry into a JSON string, which
    can be passed to the LLM in the system message.
    """

    tools_info = []
    for tool in tool_registry:
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
            "args": tool.args
        })
    return json.dumps(tools_info, indent=4)



def get_system_message(tool_registry: dict) -> SystemMessage:
    """
    Constuct the system message for the ReAct agent, relative
    to the tool registry.
    """

    tool_info = build_tool_info(tool_registry)
    format_instructions = parser.get_format_instructions()

    incremental_changes_str = """
    Only make very incremental changes to the codebase, which touch as few lines as possible.
    If the changes seem overwhelming, start with the most obvious ones:
        - renaming variables or functions
        - inverting boolean conditions
        - extracting functions
        - enabling early returns
        - checking for dead code
        - checking for duplicated code
    """ if get_settings()["make_incremental_changes"] else ""

    refactoring_tips_str = """
    Look up and decide on one specific refactoring technique, out
    of the available techniques, which you'll apply to the specific issue.
    """ if get_settings()["use_refactoring_tricks"] else ""

    update_issues_list_str = (
        "YOU MUST UPDATE THIS LIST AS YOU GO." if get_settings()["make_incremental_changes"] else ""
    )

    make_plan_string = f"""
    Your task is to make a precise list of issues in the codebase.
    {update_issues_list_str}
    """ if get_settings()["make_plan"] else ""

    msg = f"""
    You are a professional software developer.
    Your job is to refactor the existing codebases.
    You work in a loop of thought, action, and observation.

    {make_plan_string}
    For each issue, you will use a refactoring to address it.
    {refactoring_tips_str}

    You can use a variety of tools to assist you.
    {incremental_changes_str}
    After each change, run the tests to ensure that the code still works, and commit the changes to the codebase.

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
    {"FOCUS ON ONE ISSUE AT A TIME. BREAK EVERYTHING DOWN INTO SMALL STEPS." if get_settings()['make_incremental_changes'] else ""}

    {"ONCE YOU ARE DONE WITH THE LIST OF ISSUES, TRY TO RE-CHECK THE CODEBASE FOR ANY ADDITIONAL ISSUES." if get_settings()["make_plan"] else ""}
    IF YOU CAN'T FIND FURTHER ISSUES, YOU CAN STOP.

    IF YOU'RE STUCK, E.G. IF TESTS FAIL MULTIPLE TIMES IN A ROW, OR IF YOU NEED FURTHER INPUT,
    {"ASK YOUR BUDDY FOR HELP." if get_settings()["get_buddy_feedback"] else "TRY AN ALTERNATIVE APPROACH."}

    {format_instructions}
    """

    return SystemMessage(content=msg)
