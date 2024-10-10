""" This module registers all tools that are available in the system. """

from .tools import ToolFactory
from ..config import get_settings

def register_tools(repo_path, source_code_dir):
    """ Register all tools that are available in the system. """

    tool_factory = ToolFactory(repo_path, source_code_dir)

    tool_registry = [
        tool_factory.get_browse_files_tool(),
        tool_factory.get_open_file_tool(),
        tool_factory.get_overwrite_file_tool(),
        tool_factory.get_commit_changes_tool(),
        tool_factory.get_stop_tool(),
    ]

    if get_settings()["modify_specific_method"]:
        tool_registry.append(tool_factory.get_overwrite_single_method_tool())
    if get_settings()["consider_cyclomatic_complexity"]:
        tool_registry.append(tool_factory.get_cyclomatic_complexity_tool())
    if get_settings()["get_buddy_feedback"]:
        tool_registry.append(tool_factory.get_ask_buddy_tool())
    if get_settings()['use_refactoring_tricks']:
        tool_registry.append(tool_factory.get_refactoring_tipps_tool())

    return tool_registry
