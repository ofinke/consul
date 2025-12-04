# TODO: Write a tool which gives you nicely formatted diff between two branches

# TODO: Write a tool which gives you all commits and their comments in a certain branch

import subprocess


def get_branch_diff(current_branch: str, compare_branch: str) -> str:
    """
    Get a formatted diff between two branches.

    Input:
        current_branch (str): The branch you are currently on.
        compare_branch (str): The branch to compare against.
    """
    try:
        # Fetch latest changes to ensure diff is up-to-date
        subprocess.run(["git", "fetch"], check=True, capture_output=True)

        # Get diff between branches
        result = subprocess.run(
            ["git", "diff", f"{compare_branch}..{current_branch}"],
            check=True,
            capture_output=True,
            text=True,
        )

        diff_output = result.stdout.strip()
        if not diff_output:
            return f"No differences found between '{current_branch}' and '{compare_branch}'."

    except subprocess.CalledProcessError as e:
        return f"Error generating diff: {e.stderr.strip()}"
    else:
        return f"=== Diff between '{current_branch}' and '{compare_branch}' ===\n{diff_output}\n=== End of Diff ==="
