import asyncio
import uuid
from typing import ClassVar

from langchain_core.messages import BaseMessage, HumanMessage
from loguru import logger

from consul.cli.utils.callback import interface_callback

from .base import BaseFlow
from .chat import ChatTask
from .lang_react import LangReactFlow
from .react import ReactAgentFlow
from .registry import get_flow_config_registry
from .summary import SummaryTask


class FlowSession:
    """
    Chat session managment. Holds chat history and manages logging.
    Each conversation has a unique identificator for logging purposes. This ID is restarted, when history is cleared.
    """

    # session variables
    chat_history: list[BaseMessage]
    flow: BaseFlow
    cid: str

    flow_types_map: ClassVar[dict[str, type[BaseFlow]]] = {
        "ChatTask": ChatTask,
        "LangReactFlow": LangReactFlow,
        "ReactAgentFlow": ReactAgentFlow,
        "SummaryTask": SummaryTask,
    }

    def __init__(self) -> None:
        """Initialize sessíon with empty history, new conversation_id and flow registry."""
        self.registry = get_flow_config_registry()
        self.clear_history()

    @property
    def str_flow_info(self) -> str:
        """Returns information about active flow."""
        return f"flow '{self.flow.config.flow_name}'; ver: {self.flow.config.version}; {self.flow.config.description}"

    def clear_history(self) -> None:
        """Clear chat history and create a new conversation id."""
        logger.debug("Clearing session history.")
        self.chat_history = []
        self.cid = str(uuid.uuid4())

    def change_flow(self, flow_name: str) -> None:
        """Change used flow."""
        logger.debug(f"Changing flow to '{flow_name}'")
        try:
            flow_config = self.registry.get(flow_name)
        except KeyError:
            logger.warning(f"Couldn't find flow '{flow_name}', starting default flow 'chat'.")
            flow_config = self.registry.get("chat")

        self.flow = self.flow_types_map[flow_config.flow_type](flow_config)

        # SummaryTask is a special case, where we don't want to store the result under same covnersation id as the
        # original conversation, so in this case, we reset the conversation id.
        if flow_config.flow_type == "SummaryTask":
            self.cid = str(uuid.uuid4())

    def reload_flow(self, flow_name: str | None = None) -> None:
        self.clear_history()
        self.reload_flow(flow_name if flow_name else self.flow.config.flow_name)

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
        }

        # Execute the flow
        result = asyncio.run(self.flow.aexecute(input_state))

        # Store response in history and return model answer
        new_history_part = result.messages[len(self.chat_history) :]
        self.chat_history.extend(new_history_part)
        return result.messages[-1].text
