# TODO: Add a factory which automatically creates prompt variables mapping for config,
# can it even populate enum? is enum necessary if there will be factory for it?
# Similar to tools?

class PromptFormatInject:
    def __init__(self):
        self._registry = {}

    def register(self, func: callable) -> callable:
        """Decorator to register a function for formatting."""
        self._registry[func.__name__] = func
        return func

    def get_mapping(self):
        class Mapping(dict):
            def __missing__(inner_self, key):
                if key in self._registry:
                    return self._registry[key]()
                raise KeyError(key)

        return Mapping()


# Usage
prompt_format_inject = PromptFormatInject()
