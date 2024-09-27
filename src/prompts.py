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
]

LOGGER = logging.getLogger("Tools")


PROJECT_ROOT = os.path.abspath(os.path.join(__file__, "..", "..", ".."))

SAMPLE_PROJECT_FOLDER = "sample_project"


class ReActOutput(BaseModel):
    thought: str = Field(description="Your current thought.")
    action: str = Field(description="The tool to use.")
    tools_input: dict = Field(description="The input to the action.")
    observation: str = Field(description="Your observation.")

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

SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are a specialist software developer."
        "Your job is to automatically refactor existing codebases."
        "You work in a loop of thought, action, and observation."
        "You can use a variety of tools to assist you."
        "The next tool you use will depend on previous observations."
    #     "Normally, you use the following refactoring techniques: "
    # ) + ", ".join(tools.get_refactoring_techniques.invoke([])) + (
        "\n"
        "\n"
        "You can use the following tools to assist you: "
    ) + build_tool_info() + (
        "Only make incremental changes to the codebase."
        "After each change, run the tests to ensure that the code still works."
        # "You should only use the refactoring techniques in the catalog. Apply them one at a time."

        "Respond with the tool you would like to use."
        "You don't have to worry about writing tests. Rest assured that tests already exist."

        "AFTER EACH CHANGE, RUN THE TESTS TO ENSURE THAT THE CODE STILL WORKS."
        "IF THE CODE WORKS, COMMIT THE CHANGES TO THE CODEBASE."
        "IF THE CODE DOES NOT WORK, REVERT THE CHANGES AND TRY AGAIN."

        "Remember to respond in the correct format."
        "Provide your thought, action, tools input, and observation the following format: "
    ) + parser.get_format_instructions()
)
