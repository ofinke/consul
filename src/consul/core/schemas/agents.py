import os
from enum import Enum

import yaml
from pydantic import BaseModel

from consul.core.schemas.prompts import ChatTurn

# TODO: This approach doesn't work as the cls.name cannot access the .name, look into
# how to fix this while keeping it elegant.

class AvailableAgents(Enum):
    PYCRITIC = "pycritic"


class BaseAgentConfig(BaseModel):
    name: AvailableAgents
    prompt_history: list[ChatTurn]

    @classmethod
    def load_agent(cls: type["BaseAgentConfig"]) -> "BaseAgentConfig":
        """Load an agent configuration from a YAML file."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Use the value of the 'name' attribute to determine the config file name
        config_filename = f"{cls.name.value}.yaml"
        config_path = os.path.join(script_dir, "..", "configs", "prompts", config_filename)
        
        try:
            with open(config_path, "r") as file:
                data = yaml.safe_load(file)
            return cls(**data)
        except FileNotFoundError:
            raise ValueError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML: {e}")


class PycriticAgentConfig(BaseAgentConfig):
    name: AvailableAgents = AvailableAgents.PYCRITIC


# Example usage
if __name__ == "__main__":
    config = PycriticAgentConfig.load_agent()
    print(config)
