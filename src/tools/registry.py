""" This module registers all tools that are available in the system. """

from .tools import ToolFactory

def register_tools(repo_path, source_code_dir):
    """ Register all tools that are available in the system. """

    tool_factory = ToolFactory(repo_path, source_code_dir)

    tool_registry = [
        tool_factory.get_open_file_tool(),
        tool_factory.get_overwrite_file_tool(),
        tool_factory.get_overwrite_single_method_tool(),
        tool_factory.get_commit_changes_tool(),
        tool_factory.get_stop_tool(),
        # tool_factory.get_ask_buddy_tool(),
        # tool_factory.get_get_refactoring_tipps_tool(),
        tool_factory.get_cyclomatic_complexity_tool(),
    ]

    return tool_registry
