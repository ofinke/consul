"""
Test suite for the get_source_code function from consul.tools.code.
Covers function, class, async function, file extraction, context, and error handling.
All tests use the public .invoke() interface except one direct call test.
"""

from pathlib import Path

from consul.tools.code import get_source_code


# Helper to write a file
def _write_file(path: Path, content: str) -> None:
    path.write_text(content)


def test_get_source_code_function_basic(tmp_path: Path) -> None:
    """
    Test extracting a regular function from a Python file using .invoke().
    Verifies correct name, type, file, code, and docstring.
    """
    py_file = tmp_path / "foo.py"
    code = """
def foo():
    "This is foo."
    return 42
"""
    _write_file(py_file, code)
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(py_file),
            "project_root": str(tmp_path),
            "include_context": False,
        }
    )
    assert result["name"] == "foo"
    assert result["type"] == "function"
    assert result["file"].endswith("foo.py")
    assert "return 42" in result["code"]
    assert result["docstring"] == "This is foo."


def test_get_source_code_class_basic(tmp_path: Path) -> None:
    """
    Test extracting a class from a Python file using .invoke().
    Checks correct extraction and docstring.
    """
    py_file = tmp_path / "bar.py"
    code = """
class Bar:
    "Bar class doc."
    def method(self):
        pass
"""
    _write_file(py_file, code)
    result = get_source_code.invoke(
        {
            "target_type": "class",
            "name": "Bar",
            "file_path": str(py_file),
            "project_root": str(tmp_path),
            "include_context": False,
        }
    )
    assert result["name"] == "Bar"
    assert result["type"] == "class"
    assert result["file"].endswith("bar.py")
    assert "def method(self)" in result["code"]
    assert result["docstring"] == "Bar class doc."


def test_get_source_code_async_function(tmp_path: Path) -> None:
    """
    Test extracting an async function from a Python file using .invoke().
    Ensures type is 'async function' and code is correct.
    """
    py_file = tmp_path / "baz.py"
    code = """
async def baz():
    "Async doc."
    return 'hi'
"""
    _write_file(py_file, code)
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "baz",
            "file_path": str(py_file),
            "project_root": str(tmp_path),
            "include_context": False,
        }
    )
    assert result["name"] == "baz"
    assert result["type"] == "async function"
    assert result["file"].endswith("baz.py")
    assert "async def baz" in result["code"]
    assert result["docstring"] == "Async doc."


def test_get_source_code_file(tmp_path: Path) -> None:
    """
    Test extracting the entire file using target_type='file'.
    Checks that the code matches the file content.
    """
    py_file = tmp_path / "whole.py"
    code = """
def foo():
    return 1
"""
    _write_file(py_file, code)
    result = get_source_code.invoke(
        {
            "target_type": "file",
            "name": "whole.py",
            "file_path": str(py_file),
            "project_root": str(tmp_path),
            "include_context": False,
        }
    )
    assert result["type"] == "file"
    assert result["file"].endswith("whole.py")
    assert result["code"].strip() == code.strip()


def test_get_source_code_include_context(tmp_path: Path) -> None:
    """
    Test extracting a function with include_context=True.
    Checks that context and context_lines are present and correct.
    """
    py_file = tmp_path / "ctx.py"
    code = """
def before(): pass

def foo():
    "Doc."
    return 1

def after(): pass
"""
    _write_file(py_file, code)
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(py_file),
            "project_root": str(tmp_path),
            "include_context": True,
        }
    )
    assert "context" in result
    assert "context_lines" in result
    assert "def foo()" in result["context"]
    start, end = result["context_lines"]
    assert start <= result["lines"][0] <= end


def test_get_source_code_not_found(tmp_path: Path) -> None:
    """Test extracting a non-existent function returns an error."""
    py_file = tmp_path / "nofunc.py"
    code = """
def foo(): pass
"""
    _write_file(py_file, code)
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "bar",
            "file_path": str(py_file),
            "project_root": str(tmp_path),
            "include_context": False,
        }
    )
    assert "error" in result
    assert "No function named 'bar' found" in result["error"]


def test_get_source_code_file_not_found(tmp_path: Path) -> None:
    """Test extracting from a non-existent file returns an error."""
    py_file = tmp_path / "missing.py"
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(py_file),
            "project_root": str(tmp_path),
            "include_context": False,
        }
    )
    assert "error" in result
    assert "No function named 'foo' found" in result["error"]


def test_get_source_code_file_path_required(tmp_path: Path) -> None:
    """Test extracting a file without file_path returns an error."""
    result = get_source_code.invoke(
        {
            "target_type": "file",
            "name": "foo.py",
            "file_path": None,
            "project_root": str(tmp_path),
            "include_context": False,
        }
    )
    assert "error" in result
    assert "file_path required for target_type='file'" in result["error"]


def test_get_source_code_non_python_file(tmp_path: Path) -> None:
    """Test extracting from a non-Python file returns an error."""
    txt_file = tmp_path / "notpy.txt"
    _write_file(txt_file, "just some text\n")
    result = get_source_code.invoke(
        {
            "target_type": "function",
            "name": "foo",
            "file_path": str(txt_file),
            "project_root": str(tmp_path),
            "include_context": False,
        }
    )
    assert "error" in result


# def test_get_source_code_direct_call(tmp_path: Path) -> None:
#     """
#     Directly call get_source_code (not via .invoke) for a function extraction.
#     Ensures the result matches expectations.
#     """
#     py_file = tmp_path / "direct.py"
#     code = """
#             def foo():
#                 "Direct doc."
#                 return 123
#             """
#     _write_file(py_file, code)
#     result = code_module.get_source_code.func(
#         target_type="function",
#         name="foo",
#         file_path=str(py_file),
#         project_root=str(tmp_path),
#         include_context=False,
#     )
#     assert result["name"] == "foo"
#     assert result["type"] == "function"
#     assert result["file"].endswith("direct.py")
#     assert "return 123" in result["code"]
#     assert result["docstring"] == "Direct doc."
