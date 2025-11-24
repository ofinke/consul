import functools

from consul.core.abc import Registry


class PromptRegistry(Registry):

    # TODO: Idea is, that when the instance of PromptRegistry is created, i automatically registers all prompts in the
    # consul.prompt package. Si probably use similar method as in original implementation? Originally it used 
    # a decorator which triggered when the function autodiscover_plugins ran. Can I do it using class method?

    def __init__(self):
        super().__init__()


    def autoregister_prompt(self, func: callable) -> callable:
        self.register(func.__name__, func())
        return func




@functools.cache
def get_prompt_registry() -> PromptRegistry:
    return PromptRegistry()
