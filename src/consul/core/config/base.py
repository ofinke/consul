from langchain_core.messages import BaseMessage
from pydantic import BaseModel


class ChatTurnConfig(BaseModel):
    side: str
    text: str
    variables: list[str] | None = None

    def dump_tuple(self) -> tuple[str, str]:
        return (self.side.value, self.text)

    def dump_to_chatmessage(self) -> BaseMessage:
        raise NotImplementedError
