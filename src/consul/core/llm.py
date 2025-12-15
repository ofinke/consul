# TODO: Move here the model creation registry
import functools

from consul.core.abc import Registry

# TODO: Create something like ModelContext (different word then context) which defines what type of model it is
# reasoning / not-reasoning and which provider it can use. ModelScope?
# example:
# Models = {
#     "gpt-5-chat": {
#         "providers": ["litellm", "azure"],
#         "reasoning": False,
#     },
#     "gpt-5-codex": {
#         "providers": ["litellm", "azure"],
#         "reasoning": True,
#     },
# }


class LLMRegistry(Registry):
    pass


@functools.cache
def get_prompt_registry() -> LLMRegistry:
    return LLMRegistry()
