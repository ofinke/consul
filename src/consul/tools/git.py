# TODO: Write a tool which gives you nicely formatted diff between two branches

# TODO: Write a tool which gives you all commits and their comments in a certain branch

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio.subprocess import Process


async def get_branch_diff(current_branch: str, compare_branch: str) -> str:
    """
    Retrieve formatted diff between two git branches.

    Input:
        current_branch (str): The branch you are currently on.
        compare_branch (str): The branch to compare against.
    """
    try:
        # Fetch latest changes asynchronously
        fetch_proc: Process = await asyncio.create_subprocess_exec(
            "git",
            "fetch",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await fetch_proc.wait()

        # Get diff asynchronously
        diff_proc: Process = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            f"{compare_branch}..{current_branch}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await diff_proc.communicate()

        if diff_proc.returncode != 0:
            return f"Error generating diff: {stderr.decode().strip()}"

        diff_output = stdout.decode().strip()
        if not diff_output:
            return f"No differences found between '{current_branch}' and '{compare_branch}'."

    except Exception as e:  # noqa: BLE001
        return f"Unexpected error: {e!s}"

    else:
        return f"=== Diff between '{current_branch}' and '{compare_branch}' ===\n{diff_output}\n=== End of Diff ==="
