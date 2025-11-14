from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import Command

from consul.cli.utils.text import get_terminal_handler
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
        if not isinstance(message, dict):
            message = message.model_dump()
        return {
            "author": message.get("type", self.emsg),
            "message": message.get("content", self.emsg),
            "tool_call": message.get("tool_calls"),
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


class StateSchema(AgentState):
    # Information for logging
    flow: str
    cid: str
    # callback: Callable


# TODO: recreate the spinner update with callback
class InterfaceMiddleware(AgentMiddleware):
    """Wrapper for LoggingHandler for langgraph create_agent function."""

    state_schema: StateSchema = StateSchema

    def __init__(self) -> None:
        """Usual init + start database handler."""
        self.logger = LoggingHandler()
        self.io = get_terminal_handler()
        super().__init__()

    def before_model(self, state: AgentState, runtime: Runtime) -> None:  # noqa: ARG002
        """Log latest message before model call."""
        # The state need to be copied, otherwise the changes translate into the state and breaks down the flow later.
        self.logger.log_message(state)
        if isinstance(state.get("messages", [])[-1], (ToolMessage, HumanMessage)):
            self.io.restart_spinner()

    def after_model(self, state: AgentState, runtime: Runtime) -> None:  # noqa: ARG002
        """Log latest message after model call."""
        # The state need to be copied, otherwise the changes translate into the state and breaks down the flow later.
        self.logger.log_message(state)

        if hasattr(state.get("messages", [])[-1], "tool_calls"):
            calls = state.get("messages", [])[-1].tool_calls
            msg = f"Consulting {', '.join([f"'{c.get('name')}'" for c in calls])} tool(s)"
            self.io.restart_spinner(msg)
        else:
            self.io.restart_spinner()
