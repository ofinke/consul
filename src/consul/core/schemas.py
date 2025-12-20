# TODO: Move schemas from .core.config.py

from collections import defaultdict
from typing import Self

from pydantic import BaseModel, model_validator


class MCPConfig(BaseModel):
    """Definition of configuration for MCP servers."""

    command: str | None = None
    args: list | None = None
    url: str | None = None
    transport: str


class LLMParameters(BaseModel):
    temperature: float = 0
    max_tokens: int = 512
    timeout: int = 30
    # TODO: Implement reasoning effort reasonably. When reasoning effort is set to anything, the message structure
    # changes. The AIMessage content changes to list of data instead of a pure string. message.text exists, but
    # it dissapears if we are dumping the message, which we do before logging. Maybe more unknown issues arise. When
    # running this parameter with unsupported model, the request fails completely
    # reasoning: dict = {"effort": "low"}


class ChatTurnConfig(BaseModel):
    # TODO: Get rid of this in the name of simplification?
    side: str
    text: str
    variables: list[str] | None = None


class ToolConfig(BaseModel):
    """
    Configuration of default tools available to the agent.
    Expected functionality:
     - servers: list of MCP servers names to use. Server params are then loaded from database.
     - include: tools to include from specific servers: 'local:find' includes find tool from local server.
     - exclude: opposite of the include.
    """

    servers: list[str] | None = None
    include: list[str] | None = None
    exclude: list[str] | None = None

    @model_validator(mode="after")
    def validate_servers(self) -> Self:
        """Add all server names from include/exclude in the 'servers' key."""
        servers = self.servers if self.servers else []
        if self.include:
            servers.extend([row.split(":")[0] for row in self.include])
        if self.exclude:
            servers.extend([row.split(":")[0] for row in self.exclude])
        self.servers = list(set(servers))
        return self

    @property
    def include_dict(self) -> dict[str, list[str]]:
        """Returns include key as a dict in the format {"server_name": ["tool1", "tool2"]}."""
        if not self.include:
            return {}

        result: dict[str, list[str]] = defaultdict(list)
        for tool in self.include:
            if ":" not in tool:
                continue  # skip invalid entries
            name, value = tool.split(":", 1)  # split only on first colon
            result[name].append(value)
        return dict(result)

    @property
    def exclude_dict(self) -> dict[str, list[str]]:
        """Returns exclude key as a dict in the format {"server_name": ["tool1", "tool2"]}."""
        if not self.exclude:
            return {}

        result: dict[str, list[str]] = defaultdict(list)
        for tool in self.exclude:
            if ":" not in tool:
                continue  # skip invalid entries
            name, value = tool.split(":", 1)  # split only on first colon
            result[name].append(value)
        return dict(result)


class AgentParameters(BaseModel):
    max_iterations: int = 5


class FlowConfig(BaseModel):
    """Configuration of all AI flows."""

    # TODO: Optimize and replace the OG config
    # task metadata
    flow_name: str
    flow_type: str
    description: str
    version: str = "0.0.0"
    tags: list[str] = []

    # llm configuration
    llm_name: str = "gpt-5-chat"
    llm_params: LLMParameters = LLMParameters()

    # prompts:
    prompt_history: list[ChatTurnConfig]

    # agent config
    agent: AgentParameters | None = None

    # tools
    tools: ToolConfig | None = None
