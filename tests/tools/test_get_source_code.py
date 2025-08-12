"""
Updated tests for get_source_code tool.

Covers:
- Happy paths: function, async function, class, whole file
- Error cases: file not found, target not found, syntax error, unreadable file
- Always uses .invoke() to respect tool decorator
"""

from pathlib import Path
from typing import Any, Never

import pytest
from consul.tools import retrieve_code

get_source_code = retrieve_code.get_source_code


def _write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_get_source_code_function_basic(tmp_path: Path) -> None:
    """Extract a regular function and verify numbered code output."""
    py_file = tmp_path / "foo.py"
    _write_file(py_file, "def foo():\n    return 42\n")
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(py_file),
        }
    )
    assert "code" in result, f"Expected code in result, got {result}"
    assert "def foo()" in result["code"]


def test_get_source_code_async_function(tmp_path: Path) -> None:
    """Extract an async function."""
    py_file = tmp_path / "baz.py"
    _write_file(py_file, "async def baz():\n    return 'hi'\n")
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "baz",
            "file_path": str(py_file),
        }
    )
    assert "code" in result
    assert "async def baz" in result["code"]


def test_get_source_code_class_basic(tmp_path: Path) -> None:
    """Extract a class definition."""
    py_file = tmp_path / "bar.py"
    _write_file(py_file, "class Bar:\n    pass\n")
    result = get_source_code.invoke(
        {
            "target_type": "class",
            "name": "Bar",
            "file_path": str(py_file),
        }
    )
    assert "code" in result
    assert "class Bar" in result["code"]


def test_get_source_code_file(tmp_path: Path) -> None:
    """Extract the entire file."""
    py_file = tmp_path / "whole.py"
    _write_file(py_file, "def foo():\n    return 1\n")
    result = get_source_code.invoke(
        {
            "target_type": "file",
            "file_path": str(py_file),
        }
    )
    assert "code" in result
    assert "def foo()" in result["code"]


def test_get_source_code_target_not_found(tmp_path: Path) -> None:
    """Request a non-existent function returns appropriate error."""
    py_file = tmp_path / "missing_func.py"
    _write_file(py_file, "def other(): pass\n")
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(py_file),
        }
    )
    assert "error" in result
    assert "No function named 'foo'" in result["error"]


def test_get_source_code_file_not_found(tmp_path: Path) -> None:
    """Non-existent file returns file not found error."""
    py_file = tmp_path / "nope.py"
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(py_file),
        }
    )
    assert "error" in result
    assert "File not found" in result["error"]


def test_get_source_code_syntax_error(tmp_path: Path) -> None:
    """File with syntax error returns parse error."""
    py_file = tmp_path / "bad.py"
    _write_file(py_file, "def oops(:\n    pass\n")
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "oops",
            "file_path": str(py_file),
        }
    )
    assert "error" in result
    assert "Could not parse file" in result["error"]


def test_get_source_code_unreadable_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate read_file_lines raising an exception."""
    py_file = tmp_path / "unreadable.py"
    _write_file(py_file, "def foo(): pass\n")

    def bad_read(_: Any) -> Never:
        msg = "boom"
        raise OSError(msg)

    monkeypatch.setattr(retrieve_code, "read_file_lines", bad_read)
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(py_file),
        }
    )
    assert "error" in result
    assert "Could not read file" in result["error"]


# Decorator-related tests
def test_get_source_code_function_single_decorator(tmp_path: Path) -> None:
    """Ensure a single-decorated function includes the decorator line in output."""
    py_file = tmp_path / "single_func.py"
    _write_file(py_file, "@decorator\ndef foo():\n    return 42\n")
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(py_file),
        }
    )
    assert "code" in result, f"Expected code in result, got {result}"
    code = result["code"]
    assert "@decorator" in code, "Decorator line missing from extracted code"
    assert "def foo" in code


def test_get_source_code_function_multiple_decorators(tmp_path: Path) -> None:
    """Ensure multiple-decorated function includes all decorator lines in output."""
    py_file = tmp_path / "multi_func.py"
    _write_file(py_file, "@decorator_one\n@decorator_two(param=1)\ndef bar():\n    return 'ok'\n")
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "bar",
            "file_path": str(py_file),
        }
    )
    assert "code" in result
    code = result["code"]
    assert "@decorator_one" in code, "First decorator missing"
    assert "@decorator_two" in code, "Second decorator missing"
    assert "def bar" in code


def test_get_source_code_class_single_decorator(tmp_path: Path) -> None:
    """Ensure a single-decorated class includes the decorator line in output."""
    py_file = tmp_path / "single_class.py"
    _write_file(py_file, "@decorator\nclass Foo:\n    pass\n")
    result = get_source_code.invoke(
        {
            "target_type": "class",
            "name": "Foo",
            "file_path": str(py_file),
        }
    )
    assert "code" in result
    code = result["code"]
    assert "@decorator" in code, "Decorator line missing from extracted code"
    assert "class Foo" in code


def test_get_source_code_class_multiple_decorators(tmp_path: Path) -> None:
    """Ensure multiple-decorated class includes all decorator lines in output."""
    py_file = tmp_path / "multi_class.py"
    _write_file(py_file, "@decorator_one\n@decorator_two(param='x')\nclass Bar:\n    pass\n")
    result = get_source_code.invoke(
        {
            "target_type": "class",
            "name": "Bar",
            "file_path": str(py_file),
        }
    )
    assert "code" in result
    code = result["code"]
    assert "@decorator_one" in code, "First decorator missing"
    assert "@decorator_two" in code, "Second decorator missing"
    assert "class Bar" in code


def test_get_source_code_line_numbers_correct(tmp_path: Path) -> None:
    """Verify that returned code lines are correctly numbered and sequential."""
    py_file = tmp_path / "numbered.py"
    # Function starts at line 3 in the file
    _write_file(
        py_file,
        "\n\n"  # two blank lines
        "def foo():\n"
        "    x = 1\n"
        "    return x\n",
    )
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(py_file),
        }
    )
    lines = result["code"].splitlines()
    numbers = [int(line.split(":", 1)[0]) for line in lines]
    assert numbers == list(range(3, 3 + len(numbers))), f"Expected sequential numbering from 3, got {numbers}"
