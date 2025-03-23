from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    side: str
    text: str
    variables: list[str] | None = Field(default=None)
