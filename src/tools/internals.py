""" Internal helper functions for the agent tools. """

import os

def get_project_relevant_file_endings(project_root_files: list[str]) -> list[str]:
    """ Determine the programming language of a project. """

    if "package.json" in project_root_files:
        return ["js", "jsx", "ts", "tsx"]
    if "requirements.txt" in project_root_files:
        return ["py"]
    if "pom.xml" in project_root_files:
        return ["java"]

    return [""]

def parse_gitignore(gitignore_file: str) -> list[str]:
    """ Parse a gitignore file. """
    try:
        with open(gitignore_file, "r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        return []

def in_directory(file, directory):
    """ Check if a file is in a directory. """

    #make both absolute
    directory = os.path.join(os.path.realpath(directory), '')
    file = os.path.realpath(file)

    #return true, if the common prefix of both is equal to directory
    #e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
    return os.path.commonprefix([file, directory]) == directory

def get_all_code_files(project_root_dir, code_dir):
    """ Get all code files in a directory of a specific project. """

    relevant_file_endings = get_project_relevant_file_endings(
        os.listdir(os.path.abspath(project_root_dir))
    )

    if code_dir:
        dir_to_walk = os.path.join(project_root_dir, code_dir)
    else:
        dir_to_walk = project_root_dir

    code_files = []
    for root, _, files in os.walk(dir_to_walk):
        for file in files:
            if file.split(".")[-1] in relevant_file_endings:
                code_files.append(os.path.join(root, file))
    return code_files
