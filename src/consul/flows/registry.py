import functools

from consul.core.abc import Registry


class FlowRegistry(Registry):
    pass


@functools.cache
def get_flow_registry() -> FlowRegistry:
    return FlowRegistry()
