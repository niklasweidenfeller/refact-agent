from . import tools

def register_tools(repo_path, source_code_dir):
    
    tools_dict = tools.get_tools(repo_path, source_code_dir)
    
    tool_registry = [
        tools_dict['browse_files'],
        tools_dict['open_file'],
        # tools_dict['execute_tests'],
        tools_dict['overwrite_code'],
        tools_dict['commit_changes'],
        # tools_dict['undo_changes'],
        tools_dict['stop'],
        # tools_dict['ask_buddy'],
        # tools_dict['get_refactoring_tipps'],
        tools_dict['cyclomatic_complexity_tool']
    ]

    return tool_registry
