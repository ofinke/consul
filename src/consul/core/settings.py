from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


class AzureCredentials(BaseModel):
    api_key: SecretStr
    endpoint: str = Field(serialization_alias="azure_endpoint")
    api_version: str = "2024-05-01-preview"

    def get_credentials(self) -> dict[str, str]:
        data = self.model_dump(exclude="api_key", by_alias=True)
        return data | {"api_key": self.api_key.get_secret_value()}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=get_project_root() / ".env",
        env_file_encoding="utf-8",
    )

    azure: AzureCredentials


settings = Settings()
