# TODO: Move here the model creation registry
import functools

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


class LLMFactory:
    def __init__(self):
        pass

    def get_model(self):
        pass


@functools.cache
def get_model_connection() -> LLMFactory:
    return LLMFactory().get_model()
