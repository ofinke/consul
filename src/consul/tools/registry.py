from pathlib import Path
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from loguru import logger

from consul.core.abc import Registry
from consul.core.config import ToolConfig


class ToolsRegistry(Registry):
    """Instance based registry of tools from multiple MCP servers."""

    def __init__(self, config: ToolConfig) -> None:
        """Initilize tools registry based on desired tools defined in ToolConfig."""
        super().__init__()
        self.config: ToolConfig = config
        self.loaded_servers = self.load_server_configs(config.servers)
        self.mcp_client = MultiServerMCPClient(self.loaded_servers)

    @property
    def local_mcp_server(self) -> dict[str, str | list[str]]:
        """Return definition of the local MCP server."""
        # Construct address to local MCP server
        location = Path(__file__).parent / "server.py"
        return {
            "command": "python",
            "args": [str(location)],
            "transport": "stdio",
        }

    def load_server_configs(self, server_names: list[str]) -> list[dict[str, Any]]:
        """Retrieves dictionary with MCP server connections based on server names."""
        # TODO: Create MCP server connection definitions as a table in the database and retrieve the server connections
        # here. We need to create some default connections (local MCP server) which are loaded into the database first
        # time the app is started.
        server_configs = {}
        for server in server_names:
            if server == "local":
                server_configs[server] = self.local_mcp_server
            else:
                logger.warning(f"MCP server '{server}' doesn't have a defined configuration, skipping.")
        return server_configs

    async def register_tools(self) -> None:
        """Registers prefiltered tools from all configured servers."""
        # For each server, retrieve available tools and if necessary, filter them based on config include/exclude keys
        for server in self.loaded_servers:
            server_tools = await self.mcp_client.get_tools(server_name=server)
            include_tools = self.config.include_dict.get(server, [])
            exclude_tools = self.config.exclude_dict.get(server, [])
            for tool in server_tools:
                if tool.name in include_tools and tool.name not in exclude_tools:
                    self.register(tool.name, tool)


def get_tool_registry(config: ToolConfig) -> ToolsRegistry:
    """Return instance of ToolRegistry with tools based on ToolConfig definition."""
    return ToolsRegistry(config)
