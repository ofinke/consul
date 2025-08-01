from enum import Enum

from consul.tools.code import find_code_content, get_source_code, propose_code_changes
from consul.tools.files import save_to_file
from consul.tools.find import find_patterns
from consul.tools.tests import run_pytest


class AvailableTools(Enum):
    SAVE_TO_FILE = "save_to_file"
    FIND_PATTERNS = "find_patterns"
    GET_SOURCE_CODE = "get_source_code"
    FIND_CODE_CONTENT = "find_code_content"
    RUN_PYTEST = "run_pytest"
    PROPOSE_CODE_CHANGE = "propose_code_change"


TOOL_MAPPING = {
    AvailableTools.SAVE_TO_FILE: save_to_file,
    AvailableTools.FIND_PATTERNS: find_patterns,
    AvailableTools.GET_SOURCE_CODE: get_source_code,
    AvailableTools.FIND_CODE_CONTENT: find_code_content,
    AvailableTools.RUN_PYTEST: run_pytest,
    AvailableTools.PROPOSE_CODE_CHANGE: propose_code_changes
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
