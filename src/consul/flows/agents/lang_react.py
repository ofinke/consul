from typing import TYPE_CHECKING

from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from consul.core.config.flows import AvailableFlow
from consul.core.config.prompts import PROMPT_FORMAT_MAPPING
from consul.core.config.tools import TOOL_MAPPING
from consul.flows.base import BaseFlow, BaseGraphState
from consul.flows.logging import InterfaceMiddleware

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


class LangReactFlow(BaseFlow):
    """
    React agent implementation using langgraph's create_agent function.
    Function should be identical to ReactAgentFlow from consul.flows.react.
    more info at: "https://docs.langchain.com/oss/python/langchain/agents".
    """

    def __init__(self, flow_name: AvailableFlow) -> None:
        """Same as BaseFlow init + prepare variable for tools."""
        super().__init__(flow_name)
        self._tools_by_name: dict[str, BaseTool] = {}

    @property
    def input_schema(self) -> BaseGraphState:
        return BaseGraphState

    @property
    def state_schema(self) -> BaseGraphState:
        return BaseGraphState

    def build_system_prompt(self) -> str:
        """
        Builds system prompt from config.
        If flow prompt is defined using multiple messages, merges them into a single one as needed by
        create_agent function.
        """
        chat_history = [turn.text.format_map(PROMPT_FORMAT_MAPPING) for turn in self.config.prompt_history]
        if len(chat_history) > 1:
            msg = (
                f"Flow '{self.flow_name.value}' has more than 1 defining system messages.",
                "LangReactFlow needs system prompt defined as single message. Merging history into a single prompt.",
            )
            logger.warning(msg)
        return "\n".join(chat_history)

    def build_graph(self) -> CompiledStateGraph:
        """Returns langgraph pre-defined react agent."""
        logger.debug("Creating predefined langgraph react agent using 'create_agent' function")
        return create_agent(
            model=self.get_llm(),
            tools=[TOOL_MAPPING[tool] for tool in self.config.tools],
            system_prompt=self._system_prompt,
            middleware=[
                InterfaceMiddleware(),
                # ToolMonitoringMiddleware(),
            ],
        )
