from enum import Enum
from pathlib import Path

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


CONFIG_MAPPING = {}


def get_task_config(task: AvailableTasks) -> BaseTaskConfig:

    try:
        path = Path(__file__).parent / "../../../../configs/tasks/ask_question.yamls"
        path = path.resolve()
    except Exception as err:
        print()

    used_model = CONFIG_MAPPING.get(task, BaseTaskConfig)
    used_model.model_validate()

    match task:
        # default case
        case _:
            return

    raise NotImplementedError


get_task_config(AvailableTasks.ASK)

# with Path.open(yaml_path, "r", encoding="utf-8") as file:
#     config = yaml.safe_load(file)
#     print()