""" This module registers all tools that are available in the system. """

from .tools import ToolFactory
from ..config import get_settings

def register_tools(repo_path, source_code_dir):
    """ Register all tools that are available in the system. """

    tool_factory = ToolFactory(repo_path, source_code_dir)

    # register the default tools
    tool_registry = [
        tool_factory.get_browse_files_tool(),
        tool_factory.get_open_file_tool(),
        tool_factory.get_overwrite_file_tool(),
        tool_factory.get_commit_changes_tool(),
        tool_factory.get_stop_tool(),
    ]

    # register special tools depending on the settings
    iteration_agent_settings = get_settings()

    if iteration_agent_settings["modify_specific_method"]:
        tool_registry.append(
            tool_factory.get_overwrite_single_method_tool()
        )
    if iteration_agent_settings["consider_cyclomatic_complexity"]:
        tool_registry.append(
            tool_factory.get_cyclomatic_complexity_tool()
        )
    if iteration_agent_settings["get_buddy_feedback"]:
        tool_registry.append(
            tool_factory.get_ask_buddy_tool()
        )
    if iteration_agent_settings['use_refactoring_tricks']:
        tool_registry.append(
            tool_factory.get_refactoring_tipps_tool()
        )

    return tool_registry
