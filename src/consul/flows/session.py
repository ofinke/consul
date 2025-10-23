from typing import ClassVar

from langchain_core.messages import BaseMessage, ChatMessage
from loguru import logger

from consul.core.config.flows import AvailableFlow
from consul.flows.agents.react import ReactAgentFlow
from consul.flows.base import BaseFlow
from consul.flows.tasks.chat import ChatTask


class FlowSession:
    """Chat session managment. Holds chat history and manages logging."""

    # class variables
    chat_history: list[BaseMessage]
    flow: BaseFlow

    # existing flows
    available_flows: ClassVar[dict[AvailableFlow, BaseFlow]] = {
        AvailableFlow.CHAT: ChatTask(AvailableFlow.CHAT),
        AvailableFlow.CODER: ReactAgentFlow(AvailableFlow.CODER),
        AvailableFlow.TESTER: ReactAgentFlow(AvailableFlow.TESTER),
        AvailableFlow.ARCHITECT: ReactAgentFlow(AvailableFlow.ARCHITECT),
    }

    def __init__(self, flow: AvailableFlow) -> None:
        """Initialize with first flow and empty history."""
        self.chat_history = []
        self.flow = self.available_flows[flow]

    @property
    def str_flow_info(self) -> str:
        """Returns information about active flow."""
        return f"flow '{self.flow.config.name}'; ver: {self.flow.config.version}; {self.flow.config.description}"

    def clear_history(self) -> None:
        logger.debug("Clearing session history.")
        self.chat_history = []

    def change_flow(self, flow: AvailableFlow) -> None:
        logger.debug(f"Changing flow to '{flow.value}'")
        self.flow = self.available_flows[flow]

    def post_message(self, message: str) -> str:
        # convert message in desired format
        user_message = ChatMessage(role="user", content=message)
        self.chat_history.append(user_message)

        # Execute the flow
        result = self.flow.execute({"messages": self.chat_history})

        # Store response in history and return model answer
        new_history_part = result.messages[len(self.chat_history) :]
        self.chat_history.extend(new_history_part)
        return result.messages[-1].content
