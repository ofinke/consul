"""
Test suite for the find_patterns function from consul.tools.find.
Covers all supported pattern types, error handling, and usage flag.
Each test uses temporary files/directories for project-agnostic robustness.
"""

from pathlib import Path

import pytest
from consul.tools.find import find_patterns

PATTERN_TYPES = [
    "functions",
    "classes",
    "imports",
    "calls",
    "variables",
    "decorators",
]


def _write_file(path: Path, content: str) -> None:
    path.write_text(content)


@pytest.mark.parametrize(
    ("pattern_type", "code", "expected_name"),
    [
        ("functions", "def foo():\n    pass\n", "foo"),
        ("classes", "class Bar:\n    pass\n", "Bar"),
        ("imports", "import os\n", "os"),
        ("calls", "def f():\n    print('hi')\n", "print"),
        ("variables", "x = 42\n", "x"),
        ("decorators", "@staticmethod\ndef f():\n    pass\n", "staticmethod"),
    ],
)
def test_find_patterns_basic(tmp_path: Path, pattern_type: str, code: str, expected_name: str) -> None:
    """Test that find_patterns correctly identifies each supported pattern type in a temp file."""
    # Arrange
    py_file = tmp_path / "test_file.py"
    _write_file(py_file, code)

    # Act
    result = find_patterns.invoke(
        {
            "pattern_type": pattern_type,
            "search_term": None,
            "file_path": str(py_file),
            "include_usage": False,
            "project_root": str(tmp_path),
        }
    )

    # Assert
    assert "matches" in result, "Result should contain 'matches' key."
    assert "summary" in result, "Result should contain 'summary' key."
    assert result["summary"]["total_found"] >= 1, "Should find at least one match."
    found_names = [
        m.get("name") or m.get("import") or m.get("call") or m.get("variable") or m.get("decorator")
        for m in result["matches"]
    ]
    assert expected_name in found_names, f"Expected {expected_name} in matches, got {found_names}"


def test_find_patterns_invalid_pattern_type(tmp_path: Path) -> None:
    """Test that find_patterns returns an error for an invalid pattern_type."""
    # Act
    result = find_patterns.invoke(
        {
            "pattern_type": "not_a_pattern",
            "search_term": None,
            "file_path": None,
            "include_usage": False,
            "project_root": str(tmp_path),
        }
    )
    # Assert
    assert "error" in result, "Should return an error for invalid pattern_type."
    assert result["matches"] == [], "Matches should be empty on error."
    assert result["summary"]["total_found"] == 0, "Total found should be 0 on error."


def test_find_patterns_non_python_file(tmp_path: Path) -> None:
    """Test that find_patterns returns an error for a non-Python file."""
    # Arrange
    txt_file = tmp_path / "not_python.txt"
    _write_file(txt_file, "just some text\n")
    # Act
    result = find_patterns.invoke(
        {
            "pattern_type": "functions",
            "search_term": None,
            "file_path": str(txt_file),
            "include_usage": False,
            "project_root": str(tmp_path),
        }
    )
    # Assert
    assert "error" in result, "Should return an error for non-Python file."
    assert result["matches"] == [], "Matches should be empty on error."
    assert result["summary"]["total_found"] == 0, "Total found should be 0 on error."


def test_find_patterns_include_usage(tmp_path: Path) -> None:
    """Test that find_patterns returns usage locations when include_usage is True."""
    # Arrange
    py_file = tmp_path / "test_usage.py"
    _write_file(py_file, "def foo():\n    pass\n\nfoo()\n")
    # Act
    result = find_patterns.invoke(
        {
            "pattern_type": "functions",
            "search_term": "foo",
            "file_path": str(py_file),
            "include_usage": True,
            "project_root": str(tmp_path),
        }
    )
    # Assert
    assert "matches" in result, "Result should contain 'matches' key."
    assert result["summary"]["total_found"] >= 1, "Should find at least one match."
    # Check that at least one match has a usage/usage_locations key if present
    has_usage = any("usage" in m or "usage_locations" in m for m in result["matches"])
    assert has_usage, "At least one match should include usage information when include_usage is True."
