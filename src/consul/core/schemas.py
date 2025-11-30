# TODO: Move schemas from .core.config.py

from pydantic import BaseModel


class MCPConfig(BaseModel):
    """Definition of configuration for online MCP servers."""

    command: str | None = None
    args: list | None = None
    url: str | None = None
    transport: str

