"""MCP server for local Consul tools."""

import argparse

from mcp.server.fastmcp import FastMCP

from consul.tools.files import save_to_file
from consul.tools.find import find
from consul.tools.propose_code import propose_code_edit, propose_new_code
from consul.tools.retrieve_code import get_source_code
from consul.tools.tests import run_pytest

# TODO: figure out basic method to registering tools using decorator? maybe use the old autodiscover method from
# prompts? Otherwise this needs to be defined like a script

# TODO: Tools have an input and output validation, when it fails, it raises exception inside consul, how can I handle
# that the raised exception is passed into the model. (makes sense only on input tho)

TOOLS = {}


def register_tool() -> None:
    pass


def autodisover_tools() -> None:
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP server for local Consul tools")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="CRITICAL",
        help="Set the logging level (default: CRITICAL)",
    )
    args = parser.parse_args()

    mcp = FastMCP("local", log_level=args.log_level)
    mcp.tool()(propose_code_edit)
    mcp.tool()(propose_new_code)
    mcp.tool()(get_source_code)
    mcp.tool()(save_to_file)
    mcp.tool()(find)
    mcp.tool()(run_pytest)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
