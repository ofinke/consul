import asyncio
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

from consul.core.abc import Registry
from consul.core.config.flows import ToolConfig

# TODO: Create the server address dynamically, so it's not stored as an hardcoded value using the get_tool_registry
# function which takes the desired tools and then creates the Registry with them. Initializes and requests tools from
# specific servers. We can filter tools from server by calling the mcp_client.get_tools(server_name = "local") and then
# filter output.

# TODO: Ensure that tool list is created only when the tools are desired, so we don't scrape the MCP server in cases
# when we are not using the tools. This mean, that we will have to construct the registry when the graph is being build.
# So the registry is more dynamic compared to the prompt registry, which is static and should be just a singleton
# instance accross the whole app.
# flow:
# call get_tool_registry with parameter flow.config.tools
# init with this config
# get tools from all mentioned servers or from include: "server:tool_name"
# filter the tools according to include/exclude parameter
# register the tools in registry


class ToolsRegistry(Registry):
    """Registry of MCP tools."""

    def __init__(self, config: ToolConfig) -> None:
        super().__init__()
        self.mcp_client = MultiServerMCPClient(self.local_mcp_server)

    @property
    def local_mcp_server(self) -> dict[str, str | list[str]]:
        """Return definition of local MCP server."""
        # Construct address to local MCP server
        location = Path(__file__).parent / "server.py"
        return {
            "local": {
                "command": "python",
                "args": [str(location)],
                "transport": "stdio",
            }
        }

    async def register_tools(self) -> None:
        tools = await self.mcp_client.get_tools()
        for tool in tools:
            self.register(tool.name, tool)


def get_tool_registry(config: ToolConfig) -> ToolsRegistry:
    """Return instance of ToolRegistry based on ToolConfig definition."""
    return ToolsRegistry(config)


reg = get_tool_registry(None)
asyncio.run(reg.register_tools())
