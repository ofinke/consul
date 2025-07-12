from enum import Enum
from typing import Any

from pydantic import BaseModel


class MessageType(str, Enum):
    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class ChatTurn(BaseModel):
    side: MessageType
    text: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_args: dict[str, Any] | None = None

    def dump_tuple(self) -> tuple[str, str]:
        return (self.side.value, self.text)

    def is_tool_related(self) -> bool:
        return self.side in [MessageType.TOOL_CALL, MessageType.TOOL_RESULT]
