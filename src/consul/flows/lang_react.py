from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from loguru import logger

from consul.core.schemas import FlowConfig
from consul.flows.base import BaseFlow, BaseGraphState
from consul.flows.log import LoggingHandler
from consul.prompts.registry import get_prompt_registry
from consul.tools.registry import get_tool_registry


class StateSchema(AgentState):
    # Information for logging
    flow: str
    cid: str
    callback: Callable


class InterfaceMiddleware(AgentMiddleware):
    """Middleware to handle logging and triggering the callback."""

    state_schema: StateSchema = StateSchema

    def __init__(self) -> None:
        """Usual init + start database handler."""
        self.logger = LoggingHandler()
        super().__init__()

    def before_model(self, state: AgentState, runtime: Runtime) -> None:  # noqa: ARG002
        """Log latest message before model call."""
        # The state need to be copied, otherwise the changes translate into the state and breaks down the flow later.
        self.logger.log_message(state)
        # execute callback
        callback = state.get("callback")
        if callable(callback):
            callback(state=state)

    def after_model(self, state: AgentState, runtime: Runtime) -> None:  # noqa: ARG002
        """Log latest message after model call."""
        # The state need to be copied, otherwise the changes translate into the state and breaks down the flow later.
        self.logger.log_message(state)
        # inform about tool calls when verbose
        for tool_call in state["messages"][-1].tool_calls if state["messages"] else []:
            logger.debug(f"Tool '{tool_call.get('name')}' called with input: {tool_call.get('args')}")
        # execute callback
        callback = state.get("callback")
        if callable(callback):
            callback(state=state)


class LangReactFlow(BaseFlow):
    """
    React agent implementation using langgraph's create_agent function.
    Function should be identical to ReactAgentFlow from consul.flows.react.
    more info at: "https://docs.langchain.com/oss/python/langchain/agents".
    """

    def __init__(self, flow_config: FlowConfig) -> None:
        """Same as BaseFlow init + prepare variable for tools."""
        super().__init__(flow_config)
        self.tools_registry = get_tool_registry(self.config.tools)

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
        chat_history = [turn.text.format_map(get_prompt_registry().entries) for turn in self.config.prompt_history]
        if len(chat_history) > 1:
            msg = (
                f"Flow '{self.flow_name.value}' has more than 1 defining system messages.",
                "LangReactFlow needs system prompt defined as single message. Merging history into a single prompt.",
            )
            logger.warning(msg)
        return "\n".join(chat_history)

    async def build_graph(self) -> CompiledStateGraph:
        """Returns langgraph pre-defined react agent."""
        logger.debug("Creating predefined langgraph react agent using 'create_agent' function")
        await self.tools_registry.register_tools()
        return create_agent(
            model=self.get_llm(),
            tools=self.tools_registry.get_all(),
            system_prompt=self._system_prompt,
            middleware=[
                InterfaceMiddleware(),
            ],
        )
