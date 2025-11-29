from collections import defaultdict
from enum import Enum
from functools import lru_cache
from importlib import resources
from typing import Self

import yaml
from loguru import logger
from pydantic import BaseModel, model_validator


class AvailableFlow(Enum):
    CHAT = "chat"
    CODER = "coder"
    TESTER = "tester"
    ARCHITECT = "arq"


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

    def dump_tuple(self) -> tuple[str, str]:
        return (self.side.value, self.text)


class ToolConfig(BaseModel):
    """
    Configuration of default tools available to the agent.
    Expected functionality:
     - servers: list of MCP servers names to use. Server params are then loaded from database.
     - include: tools to include from specific servers: 'local:find' includes find tool from local server.
     - exclude: opposite of the include.
    """

    # TODO: Implement this so it's functional and get rid of AvailableTools.
    servers: list[str] | None = None
    include: list[str] | None = None
    exclude: list[str] | None = None

    @model_validator(mode="after")
    def validate_servers(self) -> Self:
        """Add all server names from include/exclude in the 'servers' key."""
        servers = self.servers
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


class BaseFlowConfig(BaseModel):
    # task metadata
    name: str
    description: str
    version: str = "0.0.0"
    tags: list[str] = []

    # llm configuration
    llm_name: str = "gpt-4.1"
    llm_params: LLMParameters = LLMParameters()

    # prompts:
    prompt_history: list[ChatTurnConfig]


class BaseAgentConfig(BaseFlowConfig):
    # agent config
    agent: AgentParameters

    # tools
    tools: ToolConfig


@lru_cache(maxsize=100)
def get_flow_config(task: AvailableFlow) -> BaseFlowConfig:
    """Retrieve configuration for specific task."""
    config_mapping = {
        AvailableFlow.CODER: BaseAgentConfig,
        AvailableFlow.TESTER: BaseAgentConfig,
        AvailableFlow.ARCHITECT: BaseAgentConfig,
    }

    # try to load data from default config
    try:
        resource_pkg = "consul.configs"
        resource_name = f"{task.value}.yaml"
        config_path = resources.files(resource_pkg).joinpath(resource_name)
        with config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        logger.debug(f"Loaded config for '{task.value}' from YAML file.")
    except FileNotFoundError as e:
        msg = f"Default config for {task.value} not found: {e!s}"
        logger.error(msg)
        raise FileNotFoundError(msg) from e

    # return evaluated model
    used_model = config_mapping.get(task, BaseFlowConfig)
    return used_model.model_validate(data)
