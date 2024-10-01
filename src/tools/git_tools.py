import subprocess

def has_file_changes(file_path: str) -> bool:
    """Check if a file has changes."""
    check_file_has_changes = subprocess.check_output(["git", "status", "--porcelain", file_path])
    return check_file_has_changes.decode("utf-8").strip() != ""


def stage_file(file_path: str):
    """Stage a file for commit."""
    subprocess.check_output(['git', 'add', file_path])

def commit(message: str):
    """Commit all staged files."""
    subprocess.check_output(['git', 'commit', '-m', message])

def undo_file(file_path: str):
    """Undo changes to a file."""
    subprocess.check_output(["git", "checkout", file_path])

def git_checkout(branch: str, create: bool = False):
    """Checkout a branch."""
    if create:
        subprocess.check_output(["git", "checkout", "-b", branch])
    else:
        subprocess.check_output(["git", "checkout", branch])

def merge(from_branch: str, into_branch: str, squash: bool = True):
    """ Merge a branch into another branch. """
    git_checkout(into_branch)

    if squash:
        subprocess.check_output(["git", "merge", "--squash", from_branch])
    else:
        subprocess.check_output(["git", "merge", from_branch])

    commit(f"[ReFAct]: Merge {from_branch} into {into_branch}")

def get_current_branch() -> str:
    """Get the current branch name."""
    return subprocess.check_output(["git", "branch", "--show-current"]).decode("utf-8").strip()
