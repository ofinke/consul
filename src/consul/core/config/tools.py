from enum import Enum

from consul.tools.files import save_to_file
from consul.tools.find import find
from consul.tools.propose_code import propose_code_edit, propose_new_code
from consul.tools.retrieve_code import get_source_code
from consul.tools.tests import run_pytest


class AvailableTools(Enum):
    SAVE_TO_FILE = "save_to_file"
    FIND = "find"
    GET_SOURCE_CODE = "get_source_code"
    RUN_PYTEST = "run_pytest"
    PROPOSE_CODE_EDIT = "propose_code_edit"
    PROPOSE_NEW_CODE = "propose_new_code"


TOOL_MAPPING = {
    AvailableTools.SAVE_TO_FILE: save_to_file,
    AvailableTools.FIND: find,
    AvailableTools.GET_SOURCE_CODE: get_source_code,
    AvailableTools.RUN_PYTEST: run_pytest,
    AvailableTools.PROPOSE_CODE_EDIT: propose_code_edit,
    AvailableTools.PROPOSE_NEW_CODE: propose_new_code,
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
