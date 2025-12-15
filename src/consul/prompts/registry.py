import functools

from consul.core.abc import Registry

from .general import get_current_datetime
from .project import get_project_python_version
from .tree import get_project_tree

# TODO: make registering default prompts as as much automatic as possible? or at least as painful as possible?

# TODO: Modify the registry, so the functions are stored without executing them and then execute them, when necessary.


class PromptRegistry(Registry):
    """
    Static registry for all functions which return dynamic prompt parts.
    The prompt registry is initialized with all registered functions at app startup and is meant to be shared with
    accross the llm flows.
    """

    def __init__(self):
        super().__init__()
        self.register_default_prompts()

    def register_default_prompts(self) -> None:
        prompt_functions = [
            get_current_datetime,
            get_project_python_version,
            get_project_tree,
        ]
        for func in prompt_functions:
            self.register(func.__name__, func())


@functools.cache
def get_prompt_registry() -> PromptRegistry:
    """Returns singleton instance of the PromptRegistry cached via functools.cache."""
    return PromptRegistry()
