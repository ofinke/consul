from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import Command

from consul.cli.utils.text import TerminalHandler
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
            "usage_metadata": message.get("usage_metadata")
        }

    def log_message(self, state: dict[str, Any] | AgentState) -> None:
        """Log latest message in conversation into database."""
        to_log = MessageLogTable(
            cid=state.get("cid", self.emsg),
            flow=state.get("flow", self.emsg),
            **self._extract_message_info(state.get("messages", [])[-1]),
        )
        self.handler.store([to_log])


class LoggingMiddleware(AgentMiddleware):
    """Wrapper for LoggingHandler for langgraph create_agent function."""

    def __init__(self) -> None:
        """Usual init + start database handler."""
        self.logger = LoggingHandler()
        super().__init__()

    def before_model(self, state: AgentState, runtime: Runtime) -> None:  # noqa: ARG002
        """Log latest message before model call."""
        # The state need to be copied, otherwise the changes translate into the state and breaks down the flow later.
        self.logger.log_message(state.copy())

    def after_model(self, state: AgentState, runtime: Runtime) -> None:  # noqa: ARG002
        """Log latest message after model call."""
        # The state need to be copied, otherwise the changes translate into the state and breaks down the flow later.
        self.logger.log_message(state.copy())


# TODO: currently causes problems in agent, how can I make this better?
# "cannot access local variable 'last_ai_index' where it is not associated with a value"
# How to make this universal for all flows? I want to show status message in spinner (using tool, etc), also print
# messages agent shows while calling tools. Most likely I'll add a callable into a graph state which I will trigger at
# certain positions. And implement this callable into a middleware for create_agent agent.

# class ToolMonitoringMiddleware(AgentMiddleware):
#     def wrap_tool_call(
#         self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], ToolMessage | Command]
#     ) -> ToolMessage | Command:
#         TerminalHandler.restart_spinner(f"{request.tool_call['name']} tool")
#         try:
#             result = handler(request)
#             print(f"Tool completed successfully")
#             return result
#         except Exception as e:
#             print(f"Tool failed: {e}")
#             raise
