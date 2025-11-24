# TODO: Move here the model creation registry
import functools

from consul.core.abc import Registry


class LLMRegistry(Registry):
    pass


@functools.cache
def get_prompt_registry() -> LLMRegistry:
    return LLMRegistry()
