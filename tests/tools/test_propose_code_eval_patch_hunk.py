"""
Tests for the _eval_patch_hunk function in propose_code.py.
Covers happy path, edge cases, and header auto-insertion.
"""

import pytest

from src.consul.tools.propose_code import _eval_patch_hunk


def test_happy_path_patch_is_correct() -> None:
    """Test that a correct patch (header matches hunk body) is returned unchanged."""
    patch = "--- a/file.txt\n+++ b/file.txt\n@@ -1,2 +1,2 @@\n line1\n-line2\n+line2_changed\n"
    result = _eval_patch_hunk(patch)
    assert result == patch, "Patch should be unchanged if hunk header matches body."


def test_patch_header_mismatch_is_fixed() -> None:
    """Test that a patch with mismatched hunk header counts is fixed."""
    patch = "--- a/file.txt\n+++ b/file.txt\n@@ -1,1 +1,1 @@\n line1\n-line2\n+line2_changed\n"
    # The header says 1,1 but there are 2 lines in both old and new
    expected = "--- a/file.txt\n+++ b/file.txt\n@@ -1,2 +1,2 @@\n line1\n-line2\n+line2_changed\n"
    result = _eval_patch_hunk(patch)
    assert result == expected, "Patch header should be fixed to match hunk body."


def test_patch_without_file_headers_adds_them() -> None:
    """Test that a patch without file headers (---, +++) gets them added."""
    patch = "@@ -1,1 +1,1 @@\n line1\n-line2\n+line2_changed\n"
    result = _eval_patch_hunk(patch)
    assert result.startswith("--- a/file.txt\n+++ b/file.txt\n"), "File headers should be added if missing."
    assert "@@ -1,2 +1,2 @@" in result, "Header should be fixed to match hunk body."


def test_patch_with_multiple_hunks() -> None:
    """Test that a patch with multiple hunks, some correct and some incorrect, only fixes the incorrect ones."""
    patch = (
        "--- a/file.txt\n"
        "+++ b/file.txt\n"
        "@@ -1,1 +1,1 @@\n"
        " line1\n"
        "-line2\n"
        "+line2_changed\n"
        "@@ -10,2 +10,2 @@\n"
        " line10\n"
        "-line11\n"
        "+line11_changed\n"
    )
    expected = (
        "--- a/file.txt\n"
        "+++ b/file.txt\n"
        "@@ -1,2 +1,2 @@\n"
        " line1\n"
        "-line2\n"
        "+line2_changed\n"
        "@@ -10,2 +10,2 @@\n"
        " line10\n"
        "-line11\n"
        "+line11_changed\n"
    )
    result = _eval_patch_hunk(patch)
    assert result == expected, "Only incorrect hunk headers should be fixed."


def test_patch_with_context_lines_and_section() -> None:
    """Test that a hunk header with a section (function name) is preserved and fixed if needed."""
    patch = "--- a/file.txt\n+++ b/file.txt\n@@ -5,1 +5,1 @@ def foo\n line5\n-old\n+new\n"
    expected = "--- a/file.txt\n+++ b/file.txt\n@@ -5,2 +5,2 @@ def foo\n line5\n-old\n+new\n"
    result = _eval_patch_hunk(patch)
    assert result == expected, "Section in hunk header should be preserved and header fixed."


def test_patch_with_no_hunks_is_unchanged() -> None:
    """Test that a patch with no hunk headers is returned unchanged except for file headers."""
    patch = "some random text\nnot a diff\n"
    result = _eval_patch_hunk(patch)
    assert result.startswith("--- a/file.txt\n+++ b/file.txt\n"), "File headers should be added if missing."
    assert "some random text" in result and "not a diff" in result, "Content should be preserved."  # noqa: PT018


def test_patch_with_only_double_at_symbols_raises_value_error() -> None:
    """Ensure that a patch containing a hunk header with only '@@' raises ValueError."""
    # This header matches the regex but has no valid line numbers, triggering the '@@' only check.
    patch = "--- a/file.txt\n+++ b/file.txt\n@@\n line1\n"
    with pytest.raises(
        ValueError, match="Invalid hunk header: '@@' is not a valid unified diff hunk header"
    ) as exc_info:
        _eval_patch_hunk(patch)
    assert "Invalid hunk header" in str(exc_info.value), (
        "Expected ValueError message to indicate invalid hunk header when only '@@' is present."
    )
