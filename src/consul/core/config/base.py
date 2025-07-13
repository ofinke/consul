from pydantic import BaseModel


class ChatTurn(BaseModel):
    side: str
    text: str

    def dump_tuple(self) -> tuple[str, str]:
        return (self.side.value, self.text)
