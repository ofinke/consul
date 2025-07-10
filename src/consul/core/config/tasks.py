from enum import Enum

import yaml
from pydantic import BaseModel


class AvailableTasks(Enum):
    ASK = "ask_question"


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


def get_task_config(task: AvailableTasks) -> BaseTaskConfig:
    raise NotImplementedError
