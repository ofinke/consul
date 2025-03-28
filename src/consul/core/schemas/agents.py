from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator

# Assuming ChatTurn is defined somewhere in your project
from consul.core.schemas.prompts import ChatTurn  # Adjust the import path as necessary


class AvailableAgents(Enum):
    PYCRITIC = "pycritic"


class BaseAgentConfig(BaseModel):
    name: AvailableAgents
    prompt_history: list[ChatTurn]

    @model_validator(mode="before")
    @classmethod
    def load_agent(
        cls: type["BaseAgentConfig"],
        data: any,
    ) -> "BaseAgentConfig":
        """Load an agent configuration from a YAML file."""
        # Get the config location relative to this file location
        pdir = Path(__file__).resolve().parent
        cfgpath = pdir.parents[3] / "configs" / "agents" / f"{data['name'].value}.yaml"
        # load it
        try:
            with Path.open(cfgpath, "r") as file:
                data = yaml.safe_load(file)
        # handle exceptions
        except FileNotFoundError as e:
            msg = f"Config for {data['name'].name} not found at: {cfgpath}"
            raise ValueError(msg) from e
        except yaml.YAMLError as e:
            msg = f"Error parsing YAML: {e}"
            raise ValueError(msg) from e
        # return data for evaluation
        else:
            return data


if __name__ == "__main__":
    config = BaseAgentConfig(name=AvailableAgents.PYCRITIC)
    print(config)
