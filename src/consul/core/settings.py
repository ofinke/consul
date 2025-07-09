from dotenv import find_dotenv
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        env_file=find_dotenv(raise_error_if_not_found=True),
        env_file_encoding="utf-8",
    )

    azure: AzureCredentials


settings = Settings()
