from typing import Any

from langchain.messages import AIMessage, HumanMessage, ToolMessage
from loguru import logger
from pydantic import BaseModel

from consul.db.handler import get_db_handler
from consul.db.tables import MessageLogTable
from consul.flows.base import BaseGraphState


class LoggingHandler:
    """
    Universal logging handler for all types of flows.
    Handles logging of all messages into consul database.
    """

    emsg: str = "failed to retrieve"

    def __init__(self) -> None:
        """Usual init + start database handler."""
        self.handler = get_db_handler()

    def log_message(self, state: dict[str, Any] | type[BaseModel]) -> None:
        """
        Log latest message in conversation into database.
        Supports typed dictionaries which are by default used in langgraph as states or pydantic models used in
        my custom flow definitions.
        """
        # First we have to determine if our message can be logged at all. If state is not dictionary, we do shallow dump
        # State has to include flow and conversation_id identifiers. Then we also expect, that the message we are
        # logging is in one of the langchains messages types
        if isinstance(state, BaseGraphState):
            state = state.shallow_dump()
        if "cid" not in state and "flow" not in state:
            logger.warning("State doesn't include 'cid' and 'flow' values and cannot be logged into DB.")
            return
        latest_message = state.get("messages", [])[-1]
        if not latest_message or not isinstance(latest_message, (HumanMessage, AIMessage, ToolMessage)):
            logger.warning("Latest message is empty or not in the required format and cannot be logged into DB.")
            return

        # Then we log the message
        to_log = MessageLogTable(
            cid=state.get("cid"),
            flow=state.get("flow"),
            author=latest_message.type,
            content_blocks=latest_message.content_blocks,
            tool_call_id=latest_message.tool_call_id if hasattr(latest_message, "tool_call_id") else None,
            llm=latest_message.response_metadata.get("model_name"),
            usage_metadata=latest_message.usage_metadata if hasattr(latest_message, "usage_metadata") else None,
        )
        self.handler.store([to_log])
