"""
Tests for the `find` tool function covering all pattern types and edge cases.

These tests use a temporary directory tree to ensure isolation and speed.
We verify that:
- Each pattern_type (filename, function, class, raw) returns expected matches.
- .gitignore rules are respected.
- No matches returns an empty list.

The `find` function is decorated with @tool from LangChain, so we call it via `.invoke`.
"""

import os
import textwrap
from pathlib import Path

import pytest

from src.consul.tools.find import find


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project tree with .gitignore and test files."""
    # .gitignore to ignore ignored_file.py
    (tmp_path / ".gitignore").write_text("ignored_file.py\n")

    # Python file with a function
    (tmp_path / "func_file.py").write_text(
        textwrap.dedent(
            """
            def my_test_function():
                return 'ok'
            """
        )
    )

    # Python file with a class
    (tmp_path / "class_file.py").write_text(
        textwrap.dedent(
            """
            class MyTestClass:
                pass
            """
        )
    )

    # Python file with a raw string
    (tmp_path / "raw_file.py").write_text("print('special_string_marker')\n")

    # Ignored file containing a function that should not be found
    (tmp_path / "ignored_file.py").write_text("def ignored_function(): pass\n")

    # Non-Python file
    (tmp_path / "notes.txt").write_text("some notes here\n")

    return tmp_path


def test_find_filename_matches_expected_file(temp_project: Path) -> None:
    """Searching by filename should return only files whose name contains the search term."""
    result = find.invoke(
        {
            "pattern_type": "filename",
            "search_term": "func_file",
            "project_root": str(temp_project),
        }
    )
    matches = result["matches"]
    assert len(matches) == 1
    assert matches[0].endswith("func_file.py"), f"Expected only func_file.py, got {matches}"


def test_find_function_finds_correct_file(temp_project: Path) -> None:
    """Searching for a function should return the file containing its definition."""
    result = find.invoke(
        {
            "pattern_type": "function",
            "search_term": "my_test_function",
            "project_root": str(temp_project),
        }
    )
    matches = result["matches"]
    assert any(m.endswith("func_file.py") for m in matches), f"Expected func_file.py in matches, got {matches}"


def test_find_class_finds_correct_file(temp_project: Path) -> None:
    """Searching for a class should return the file containing its definition."""
    result = find.invoke(
        {
            "pattern_type": "class",
            "search_term": "MyTestClass",
            "project_root": str(temp_project),
        }
    )
    matches = result["matches"]
    assert any(m.endswith("class_file.py") for m in matches), f"Expected class_file.py in matches, got {matches}"


def test_find_raw_finds_correct_file(temp_project: Path) -> None:
    """Searching for a raw string should return the file containing that string."""
    result = find.invoke(
        {
            "pattern_type": "raw",
            "search_term": "special_string_marker",
            "project_root": str(temp_project),
        }
    )
    matches = result["matches"]
    assert any(m.endswith("raw_file.py") for m in matches), f"Expected raw_file.py in matches, got {matches}"


def test_find_respects_gitignore(temp_project: Path) -> None:
    """Files listed in .gitignore should not appear in matches."""
    cwd_before = Path.cwd()
    try:
        # Change working directory so load_ignore_patterns picks up the temp .gitignore
        os.chdir(temp_project)
        result = find.invoke(
            {
                "pattern_type": "function",
                "search_term": "ignored_function",
                "project_root": str(temp_project),
            }
        )
    finally:
        os.chdir(cwd_before)

    matches = result["matches"]
    assert matches == [], f"Expected no matches due to .gitignore, got {matches}"


def test_find_returns_empty_when_no_match(temp_project: Path) -> None:
    """Searching for a non-existent term should return an empty list."""
    result = find.invoke(
        {
            "pattern_type": "raw",
            "search_term": "this_does_not_exist_anywhere",
            "project_root": str(temp_project),
        }
    )
    matches = result["matches"]
    assert matches == [], f"Expected no matches, got {matches}"
