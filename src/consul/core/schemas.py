# TODO: Move schemas from .core.config.py

from pydantic import BaseModel


class MCPConfig(BaseModel):
    """Definition of configuration for online MCP servers."""

    url: str
    transport: str
