from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from loguru import logger

from consul.core.abc import Registry
from consul.core.schemas import ToolConfig
from consul.db.handler import get_db_handler


class ToolsRegistry(Registry):
    """Instance based registry of tools from multiple MCP servers."""

    def __init__(self, config: ToolConfig) -> None:
        """Initilize tools registry based on desired tools defined in ToolConfig."""
        super().__init__()
        self.config: ToolConfig = config

    def start_mcp_client(self) -> None:
        self.loaded_servers = self.load_server_configs(self.config.servers)
        self.mcp_client = MultiServerMCPClient(self.loaded_servers)

    def load_server_configs(self, server_names: list[str]) -> list[dict[str, Any]]:
        """Retrieves dictionary with MCP server connections based on server names."""
        server_configs = {}
        for server in server_names:
            try:
                server_configs[server] = self._get_server_config(server)
            except ValueError:
                logger.warning(f"Skipped MCP server '{server}' due to missing configuration.")
                continue
            logger.debug(f"Loaded MCP server '{server}' configuration.")

        return server_configs

    def _get_server_config(self, server_name: str) -> dict[str, str]:
        """Retrieves MCP server configuration from database."""
        handler = get_db_handler()
        server_config = handler.load_config(name=server_name)[0]
        return server_config.model_dump(exclude_none=True)

    async def register_tools(self) -> None:
        """Registers prefiltered tools from all configured servers."""
        self.start_mcp_client()
        # For each server, retrieve available tools and if necessary, filter them based on config include/exclude keys
        for server in self.loaded_servers:
            server_tools = await self.mcp_client.get_tools(server_name=server)
            include = set(self.config.include_dict.get(server, []))
            exclude = set(self.config.exclude_dict.get(server, []))
            all_tool_names = {tool.name for tool in server_tools}
            logger.debug(f"Retrieved MCP server '{server}' tools: {all_tool_names=}")

            # Determine allowed tools
            allowed_tools = include - exclude if include else all_tool_names - exclude
            logger.debug(f"Filtered MCP server '{server}' tools: {allowed_tools=}")

            # Register only allowed tools
            for tool in server_tools:
                if tool.name in allowed_tools:
                    self.register(tool.name, tool)


def get_tool_registry(config: ToolConfig) -> ToolsRegistry:
    """Return instance of ToolRegistry with tools based on ToolConfig definition."""
    return ToolsRegistry(config)
