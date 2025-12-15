import functools

from consul.core.abc import Registry
from consul.db.handler import get_db_handler

# TODO: The registry will take all flow configurations from database and registers them. Then the get either retrieves
# the flow completely or just the flow configuration


class FlowConfigRegistry(Registry):
    def __init__(self) -> None:
        super().__init__()
        self.register_flows()

    def register_flows(self) -> None:
        """Loads all flows from database and registers their configurations."""
        handler = get_db_handler()
        flow_configs = handler.load_config(data_schema="FlowConfig")
        for config in flow_configs:
            self.register(name=config.flow_name, value=config)


@functools.cache
def get_flow_config_registry() -> FlowConfigRegistry:
    return FlowConfigRegistry()
