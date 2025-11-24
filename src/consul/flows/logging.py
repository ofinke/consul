from typing import Any

from langchain.agents.middleware import AgentState
from langchain.messages import AIMessage, HumanMessage, ToolMessage

from consul.db.handler import get_db_handler
from consul.db.tables import MessageLogTable


class LoggingHandler:
    """
    Universal logging handler for all types of flows.
    Handles logging of all messages into consul database.
    """

    emsg: str = "failed to retrieve"

    def __init__(self) -> None:
        """Usual init + start database handler."""
        self.handler = get_db_handler()

    def _extract_message_info(self, message: dict[str, Any] | HumanMessage | AIMessage | ToolMessage) -> dict[str, Any]:
        """Convert response message into a format usable in the MessageLogTable."""
        # First, try to dump message into a dictionary.
        # TODO: This is messy as None and "" have different meaning in text variable. Change logging to store the
        # content blocks directly instead? But note that content_blocks work only for langgraphs Message class.
        text = None
        if isinstance(message, (HumanMessage, AIMessage, ToolMessage)):

            text = message.text
            message = message.model_dump()
        return {
            "author": message.get("type", self.emsg),
            "message": text if text is not None else message.get("content", self.emsg),
            "tool_call": message.get("tool_calls"),
            "tool_call_id": message.get("tool_call_id"),
            "llm": message.get("response_metadata", {}).get("model_name"),
            "usage_metadata": message.get("usage_metadata"),
        }

    def log_message(self, state: dict[str, Any] | AgentState) -> None:
        """Log latest message in conversation into database."""
        to_log = MessageLogTable(
            cid=state.get("cid", self.emsg),
            flow=state.get("flow", self.emsg),
            **self._extract_message_info(state.get("messages", [])[-1]),
        )
        self.handler.store([to_log])
