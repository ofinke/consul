import pytest
from consul.tools.propose_code import _apply_patch

# Dummy content for testing
DUMMY_CONTENT = """line1
line2
line3
"""

# Valid patch: add a line after line2
PATCH_ADD = """--- a/dummy.txt
+++ b/dummy.txt
@@ -1,3 +1,4 @@
 line1
 line2
+line2.5
 line3
"""

# Valid patch: delete line2
PATCH_DELETE = """--- a/dummy.txt
+++ b/dummy.txt
@@ -1,3 +1,2 @@
 line1
-line2
 line3
"""

# Valid patch: modify line2
PATCH_MODIFY = """--- a/dummy.txt
+++ b/dummy.txt
@@ -1,3 +1,3 @@
 line1
-line2
+LINE2_MODIFIED
 line3
"""

# Patch with missing headers
PATCH_NO_HEADER = """@@ -1,3 +1,4 @@
 line1
 line2
+line2.5
 line3
"""

# Malformed patch (bad hunk)
PATCH_MALFORMED = """--- a/dummy.txt
+++ b/dummy.txt
@@ -10,3 +10,4 @@
 line1
 line2
+line2.5
 line3
"""

# Multi-file patch (only first file should be applied)
PATCH_MULTIFILE = """--- a/dummy.txt
+++ b/dummy.txt
@@ -1,3 +1,4 @@
 line1
 line2
+line2.5
 line3
--- a/other.txt
+++ b/other.txt
@@ -1,1 +1,2 @@
 foo
+bar
"""


@pytest.mark.parametrize(
    ("original", "patch", "expected"),
    [
        (DUMMY_CONTENT, PATCH_ADD, "line1\nline2\nline2.5\nline3\n"),
        (DUMMY_CONTENT, PATCH_DELETE, "line1\nline3\n"),
        (DUMMY_CONTENT, PATCH_MODIFY, "line1\nLINE2_MODIFIED\nline3\n"),
    ],
)
def test_apply_patch_happy_path(original: str, patch: str, expected: str) -> None:
    """Test that _apply_patch correctly applies valid unified diff patches for addition, deletion, and modification."""
    # Arrange done by parametrize
    # Act
    result = _apply_patch(original, patch)
    # Assert
    assert result == expected, "Patch was not applied as expected."


def test_apply_patch_to_empty_content() -> None:
    """Test applying a valid patch to empty content (should only work if patch is designed for empty input)."""
    empty_content = ""
    patch = """--- a/dummy.txt
+++ b/dummy.txt
@@ -0,0 +1,2 @@
+foo
+bar
"""
    expected = "foo\nbar\n"
    result = _apply_patch(empty_content, patch)
    assert result == expected, "Patch to empty content failed."


def test_apply_patch_missing_headers_raises() -> None:
    """Test that a patch missing file headers raises ValueError."""
    with pytest.raises(ValueError, match="Patch must include file headers"):
        _apply_patch(DUMMY_CONTENT, PATCH_NO_HEADER)


def test_apply_patch_malformed_patch_raises() -> None:
    """Test that a malformed patch (bad hunk location) raises ValueError or unidiff error."""
    with pytest.raises(Exception):  # noqa: B017, PT011
        _apply_patch(DUMMY_CONTENT, PATCH_MALFORMED)


def test_apply_patch_multifile_only_first_applied() -> None:
    """Test that when a multi-file patch is provided, only the first file's patch is applied and no error is raised."""
    expected = "line1\nline2\nline2.5\nline3\n"
    result = _apply_patch(DUMMY_CONTENT, PATCH_MULTIFILE)
    assert result == expected, "Multi-file patch did not apply only the first file's patch."


def test_apply_patch_empty_patch_raises() -> None:
    """Test that an empty patch raises ValueError due to missing headers."""
    with pytest.raises(ValueError, match="Patch must include file headers"):
        _apply_patch(DUMMY_CONTENT, "")


def test_apply_patch_multiple_sequential_hunks() -> None:
    """
    Test that _apply_patch correctly applies multiple non-overlapping hunks
    (e.g., one hunk at the top, one at the bottom) to the same file.
    This ensures the function can handle patches that modify different parts of the file.
    """
    original = "line1\nline2\nline3\nline4\nline5\n"
    patch = (
        "--- a/dummy.txt\n"
        "+++ b/dummy.txt\n"
        "@@ -1,2 +1,3 @@\n"
        " line1\n"
        "+inserted at top\n"
        " line2\n"
        "@@ -4,2 +5,3 @@\n"
        " line4\n"
        "+inserted at bottom\n"
        " line5\n"
    )
    expected = "line1\ninserted at top\nline2\nline3\nline4\ninserted at bottom\nline5\n"
    result = _apply_patch(original, patch)
    assert result == expected, "Patch with multiple sequential hunks was not applied as expected."


def test_apply_patch_multiple_adjacent_hunks() -> None:
    """
    Test that _apply_patch correctly applies multiple adjacent hunks (hunks that touch or are separated by a single line).
    This checks that the function handles line number adjustments between hunks.
    """
    original = "a\nb\nc\nd\ne\n"
    patch = "--- a/dummy.txt\n+++ b/dummy.txt\n@@ -2,2 +2,3 @@\n b\n+x\n c\n@@ -4,2 +5,3 @@\n d\n+y\n e\n"
    expected = "a\nb\nx\nc\nd\ny\ne\n"
    result = _apply_patch(original, patch)
    assert result == expected, "Patch with multiple adjacent hunks was not applied as expected."


def test_apply_patch_multiple_mixed_hunks() -> None:
    """
    Test that _apply_patch correctly applies multiple hunks with mixed operations (add, delete, modify).
    This ensures the function can handle a realistic patch scenario.
    """
    original = "foo\nbar\nbaz\nqux\nquux\n"
    patch = (
        "--- a/dummy.txt\n+++ b/dummy.txt\n@@ -1,2 +1,2 @@\n foo\n-bar\n+BAR_MODIFIED\n@@ -4,2 +4,0 @@\n-qux\n-quux\n"
    )
    expected = "foo\nBAR_MODIFIED\nbaz\n"
    result = _apply_patch(original, patch)
    assert result == expected, "Patch with multiple mixed hunks was not applied as expected."
