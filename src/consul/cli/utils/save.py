from langchain_core.messages import AIMessage, BaseMessage, ChatMessage, ToolMessage

from consul.tools.files import save_to_file


def save_memory(memory: list[BaseMessage]) -> str:
    def process_aimessage(turn: AIMessage) -> str:
        pass

    def process_toolmessage(turn: ToolMessage) -> str:
        pass

    def process_chatmessage(turn: ChatMessage) -> str:
        pass

    text_to_save: list[str] = []

    for turn in memory:
        if isinstance(turn, AIMessage):
            text_to_save.append(process_aimessage(turn))

        if isinstance(turn, ToolMessage):
            text_to_save.append(process_toolmessage(turn))

        if isinstance(turn, ChatMessage):
            text_to_save.append(process_chatmessage(turn))

    return
