import subprocess

from langchain_core.tools import tool


@tool
def run_pytest(
    path: str = ".",
    test_name: str | None = None,
    extra_args: list[str] | None = None,
    show_logs: bool = True,  # noqa: FBT001, FBT002
) -> tuple[str, int]:
    """
    Run pytest tests using a subprocess and return the raw output and exit code.

    Args:
        path (str): Path to the test directory or file. Defaults to current directory.
        test_name (Optional[str]): Specific test function or class to run (e.g., 'TestClass::test_func').
        extra_args (Optional[List[str]]): Additional arguments to pass to pytest CLI.
        show_logs (bool): If False, suppress pytest log output (adds '--disable-warnings' and '-p no:warnings').

    Returns:
        Tuple[str, int]:
            - Raw output from pytest (stdout and stderr combined).
            - Exit code (0 if all tests passed, nonzero otherwise).

    Example:
        output, code = run_pytest(path="tests/", test_name="TestFoo::test_bar", extra_args=["-v"])

    """
    cmd = ["pytest"]
    if path:
        cmd.append(path)
    if test_name:
        cmd[-1] += f"::{test_name}"
    if extra_args:
        cmd.extend(extra_args)
    if not show_logs:
        cmd.extend(["--disable-warnings", "-p", "no:warnings"])

    result = subprocess.run(  # noqa: S603
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + "\n" + result.stderr
    return output, result.returncode
