from enum import Enum
from functools import lru_cache
from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel

from consul.core.config.base import ChatTurn


class AvailableTasks(Enum):
    ASK = "ask_question"
    TEST = "test"


class LLMParameters(BaseModel):
    temperature: float = 0
    max_tokens: int = 512
    timeout: int = 30


class BaseTaskConfig(BaseModel):
    # task metadata
    name: str
    description: str
    version: str = "0.0.0"
    tags: list[str] = []

    # llm configuration
    llm_name: str = "gpt-4.1"
    llm_params: LLMParameters = LLMParameters()

    # prompts:
    prompt_history: list[ChatTurn]


@lru_cache(maxsize=100)
def get_task_config(task: AvailableTasks) -> BaseTaskConfig:
    """Retrieve configuration for specific task."""
    config_mapping = {}

    # try to load data from default config
    try:
        path = Path(__file__).parent / f"../../../../configs/tasks/{task.value}.yaml"
        path = path.resolve()
        with Path.open(path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except FileNotFoundError as e:
        msg = f"Default config for {task.value} not found: {e!s}"
        logger.error(msg)
        raise FileNotFoundError(msg) from e

    # return evaluated model
    used_model = config_mapping.get(task, BaseTaskConfig)
    return used_model.model_validate(data)
