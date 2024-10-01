import json, logging
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage
from langchain.output_parsers import PydanticOutputParser


LOGGER = logging.getLogger("Tools")


class ReActOutput(BaseModel):
    thought: str = Field(description="Your current thought.")
    action: str = Field(description="The tool to use.")
    tools_input: dict = Field(description="The input to the action.")
    observation: str = Field(description="Your observation.")
    # plan: list[str] = Field(description="Your long-term plan. Should be a list of steps. Consider, how you want the code to look like in the future.")
    issues: list[str] = Field(
        description="""
        A list of all issues and code smells that you can find in the codebase. Pay attention for anti-patterns,
        code smells, and more. Also pay attention to the code quality and testability. Each issue should be broken
        down, when possible.
        Explain why the issue is there and what the best way to address it is. Update this list as you go.
        """
    )

parser = PydanticOutputParser(pydantic_object=ReActOutput)

def build_tool_info(tool_registry):
    tools_info = []
    for tool in tool_registry:
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
            "args": tool.args
        })
    return json.dumps(tools_info, indent=4)



def get_system_message(tool_registry):

    tool_info = build_tool_info(tool_registry)
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
    If the changes seem overwhelming, start with the most obvious ones:
        - renaming variables or functions
        - inverting boolean conditions
        - extracting functions
        - enabling early returns
        - checking for dead code
        - checking for duplicated code
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

    ONCE YOU ARE DONE WITH THE LIST OF ISSUES, TRY TO RE-CHECK THE CODEBASE FOR ANY ADDITIONAL ISSUES.
    IF YOU CAN'T FIND ANY, YOU CAN STOP.
    
    IF YOU'RE STUCK, E.G. IF TESTS FAIL MULTIPLE TIMES IN A ROW, OR IF YOU NEED FURTHER INPUT,
    TRY A ALTERNATIVE APPROACH.
    
    ALWAYS RESPOND WITH THE ENTIRE FILE CONTENT, NOT JUST SNIPPETS.

    {format_instructions}
    """

    return SystemMessage(content=msg)
