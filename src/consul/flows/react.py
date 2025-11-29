import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ChatMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from loguru import logger

from consul.core.config import AvailableFlow
from consul.flows.base import BaseFlow, BaseGraphState
from consul.flows.logging import LoggingHandler
from consul.prompts.registry import get_prompt_registry
from consul.tools.registry import get_tool_registry

# BUG: Currently tools are borked because the tool_registry needs .register_tools() method execution which is
# async and should be executed in the same loop as the whole agent runtime and I'm too lazy to figure it now as I
# don't really use this implementation anymore.


class ReactAgentFlow(BaseFlow):
    """Base class for agent tasks with tool support."""

    def __init__(self, flow_name: AvailableFlow) -> None:
        """Same as BaseFlow init + prepare variable for tools."""
        super().__init__(flow_name)
        self._tools_by_name: dict[str, BaseTool] = {}
        self.logging = LoggingHandler()
        self.tools_registry = get_tool_registry(self.config.tools)

    @property
    def input_schema(self) -> BaseGraphState:
        return BaseGraphState

    @property
    def state_schema(self) -> BaseGraphState:
        return BaseGraphState

    def get_tools(self) -> list[BaseTool]:
        """Return list of tools available to the agent."""
        return self.tools_registry.get_all()

    def build_system_prompt(self) -> list[ChatMessage]:
        """Builds system prompt from config."""
        return [
            ChatMessage(
                role=turn.side,
                content=turn.text.format_map(get_prompt_registry().entries),
            )
            for turn in self.config.prompt_history
        ]

    def get_llm(self) -> BaseChatModel:
        """Get LLM bound to tools."""
        self._llm = super().get_llm()
        tools = self.get_tools()
        return self._llm.bind_tools(tools)

    async def build_graph(self) -> StateGraph:
        """Build the agent graph with model and tool nodes."""
        # Setup tools
        tools = self.get_tools()
        self._tools_by_name = {tool.name: tool for tool in tools}

        # Create graph
        graph = StateGraph(self.state_schema)

        # node definitions
        async def llm_node(state: BaseGraphState) -> BaseGraphState:
            """Logs user message, calls LLM, logs LLM answer, and appends LLM response to chat history."""
            full_history = [*self._system_prompt, *state.messages]
            self.logging.log_message(self.state_schema(messages=full_history, **state.model_dump(exclude="messages")))
            response = await self._llm.ainvoke(full_history)
            new_state = self.state_schema(messages=[*state.messages, response], **state.model_dump(exclude="messages"))
            self.logging.log_message(new_state)
            return new_state

        async def tool_node(state: BaseGraphState) -> BaseGraphState:
            """Checks if last message contains tool call and executes it."""
            last_message = state.messages[-1]
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return state

            tool_outputs = []
            for tool_call in last_message.tool_calls:
                logger.debug(
                    f"Task '{self.config.name}' executing tool call '{tool_call['name']}' with args={str(tool_call['args'])[:25]!r}..."  # noqa: E501
                )
                tool_result = await self._tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
                tool_outputs.append(
                    ToolMessage(
                        content=json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result,
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )
                logger.success(f"Tool '{tool_call['name']}' responded with: '{tool_outputs[-1].text[:25]!r}...'")
            return self.state_schema(messages=[*state.messages, *tool_outputs], **state.model_dump(exclude="messages"))

        def should_continue(state: BaseGraphState) -> str:
            """Determine if agent should continue or end."""
            if not state.messages:
                return "end"

            last_message = state.messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "continue"
            return "end"

        # Add nodes
        graph.add_node("agent", llm_node)
        graph.add_node("tools", tool_node)

        # Set entry point
        graph.set_entry_point("agent")

        # Add conditional edges
        graph.add_conditional_edges(
            "agent",
            should_continue,
            {
                "continue": "tools",
                "end": END,
            },
        )

        # Add edge from tools back to agent
        graph.add_edge("tools", "agent")

        return graph
