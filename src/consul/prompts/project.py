import tomllib
from pathlib import Path

from consul.core.config.prompts import register_prompt_format


@register_prompt_format
def get_project_python_version() -> str:
    """Gets the project's Python version from .python-version or pyproject.toml."""
    # project dir
    project_dir = Path()

    # pyproject
    pyproject_path = project_dir / "pyproject.toml"
    if pyproject_path.is_file():
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)
            # [tool.uv] table
            uv_table = data.get("tool", {}).get("uv", {})
            if "python" in uv_table:
                return uv_table["python"]
            # [project] table
            requires_python = data.get("project", {}).get("requires-python")
            if requires_python:
                return requires_python

    # .python-version
    pyver_path = project_dir / ".python-version"
    if pyver_path.is_file():
        v = pyver_path.read_text(encoding="utf-8").strip()
        if v:
            return v

    return "Python version not found"
