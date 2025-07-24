from enum import Enum

from consul.tools.files import load_file, save_to_file
from consul.tools.find import find_patterns


class AvailableTools(Enum):
    LOAD_FILE = "load_file"
    SAVE_TO_FILE = "save_to_file"
    FIND_PATTERNS = "find_patterns"


TOOL_MAPPING = {
    AvailableTools.LOAD_FILE: load_file,
    AvailableTools.SAVE_TO_FILE: save_to_file,
    AvailableTools.FIND_PATTERNS: find_patterns,
}


# NOTE: small prep for MCP tools, issue is, that the StructuredTool from langchain doesn't support sync operations,
# so refactoring to asyncio is required for the graphs integration.

# from langchain_core.tools.structured import StructuredTool
# from langchain_mcp_adapters.client import MultiServerMCPClient
# from loguru import logger


# async def get_mcp_tools() -> list[StructuredTool]:
#     client = MultiServerMCPClient(
#         {
#             "local_tools": {
#                 "command": "python",
#                 "args": ["./src/consul/tools/stdio_mcp.py"],
#                 "transport": "stdio",
#             },
#         }
#     )

#     tools = await client.get_tools()
#     logger.debug(f"Retrieved MCP tools: {', '.join(str(tool.name) for tool in tools)}")
#     return tools
