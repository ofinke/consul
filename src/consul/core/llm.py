# TODO: Move here the model creation registry
import functools

from consul.core.schemas import LLMParameters

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
    """Factory class to create connections to language models based on the model name and provider."""

    def __init__(self):
        pass

    def get_connection(self, model_name: str, model_parameters: LLMParameters):
        """Returns a connector to a specified language model."""
        pass


@functools.cache
def get_model_connection(model_name: str, model_parameters: LLMParameters) -> LLMFactory:
    return LLMFactory().get_connection(model_name, model_parameters)
