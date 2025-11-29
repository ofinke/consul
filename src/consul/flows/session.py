import asyncio
import uuid
from typing import ClassVar

from langchain_core.messages import BaseMessage, HumanMessage
from loguru import logger

from consul.cli.utils.callback import interface_callback
from consul.core.config import AvailableFlow
from consul.flows.base import BaseFlow
from consul.flows.chat import ChatTask
from consul.flows.lang_react import LangReactFlow


class FlowSession:
    """
    Chat session managment. Holds chat history and manages logging.
    Each conversation has a unique identificator for logging purposes. This ID is restarted, when history is cleared.
    """

    # session variables
    chat_history: list[BaseMessage]
    flow: BaseFlow
    cid: str

    # existing flows
    # TODO: Creation of this class causes debug logger printing which I don't want, but should be solved by the
    # flow registry hopefully
    available_flows: ClassVar[dict[AvailableFlow, BaseFlow]] = {
        AvailableFlow.CHAT: ChatTask(AvailableFlow.CHAT),
        AvailableFlow.CODER: LangReactFlow(AvailableFlow.CODER),
        AvailableFlow.TESTER: LangReactFlow(AvailableFlow.TESTER),
        AvailableFlow.ARCHITECT: LangReactFlow(AvailableFlow.ARCHITECT),
    }

    def __init__(self, flow: AvailableFlow) -> None:
        """Initialize with first flow and empty history."""
        self.chat_history = []
        self.flow = self.available_flows[flow]
        self.cid = str(uuid.uuid4())

    @property
    def str_flow_info(self) -> str:
        """Returns information about active flow."""
        return f"flow '{self.flow.config.name}'; ver: {self.flow.config.version}; {self.flow.config.description}"

    def clear_history(self) -> None:
        """Clear chat history and create a new conversation id."""
        logger.debug("Clearing session history.")
        self.chat_history = []
        self.cid = str(uuid.uuid4())

    def change_flow(self, flow: AvailableFlow) -> None:
        """Change used flow."""
        logger.debug(f"Changing flow to '{flow.value}'")
        self.flow = self.available_flows[flow]

    def post_message(self, message: str) -> str:
        """Call flow with full history and new user message and returns the AI answer."""
        # convert message in desired format
        user_message = HumanMessage(content=message)
        self.chat_history.append(user_message)

        # define input dictionary state
        input_state = {
            "messages": self.chat_history,
            "cid": self.cid,
            "callback": interface_callback,
            # "flow": self.flow.value,
        }

        # Execute the flow
        result = asyncio.run(self.flow.aexecute(input_state))

        # Store response in history and return model answer
        new_history_part = result.messages[len(self.chat_history) :]
        self.chat_history.extend(new_history_part)
        return result.messages[-1].text
