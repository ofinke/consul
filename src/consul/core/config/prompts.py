import importlib
from pathlib import Path

PROMPT_FORMAT_MAPPING = {}


def autodiscover_plugins() -> None:
    """Auto-import plugin modules in the consul.prompts."""
    current_file = Path(__file__)
    current_dir = current_file.parent.parent.parent / "prompts"

    # Determine package
    base_package = "consul.prompts"

    for pyfile in current_dir.glob("*.py"):
        if pyfile.name == current_file.name or pyfile.name.startswith("__"):
            continue
        module_name = f"{base_package}.{pyfile.stem}"
        importlib.import_module(module_name)


def register_prompt_format(func: callable) -> callable:
    """Register prompt format into a registry."""
    PROMPT_FORMAT_MAPPING[func.__name__] = func()
    return func


# Running this causes, that when the module is imported, all functions with the
# register_prompt_format are executed and their output is stored in the
# PROMPT_FORMAT_MAPPING
autodiscover_plugins()
