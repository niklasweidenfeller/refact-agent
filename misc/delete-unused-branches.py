import subprocess

def get_branches_to_delete():
    all_branches = subprocess.check_output(["git", "branch", "--all"]).decode("utf-8").strip().replace(" ", "").replace("*", "").splitlines()
    all_branches = [branch for branch in all_branches if not branch.startswith("remotes/")]
    all_branches = [branch for branch in all_branches if branch.startswith("ReFAct")]
    return all_branches

def git_checkout(branch_name):
    subprocess.run(["git", "checkout", branch_name])

def git_branch_delete(branch_name, force=False):
    args = ["git", "branch", "-D" if force else "-d", branch_name]
    subprocess.run(args)

def git_branch_show(show_all=False):
    args = ["git", "branch"]
    if show_all:
        args.append("--all")
    subprocess.run(args)

if __name__ == "__main__":
    git_checkout("main")
    all_branches = get_branches_to_delete()
    for b in all_branches:
        git_branch_delete(b, force=True)
    git_branch_show(show_all=True)
