import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ChatMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from loguru import logger

from consul.core.config.flow import AvailableFlow
from consul.core.config.tools import TOOL_MAPPING
from consul.flow.base import BaseFlow, BaseGraphState


class ReactAgentFlow(BaseFlow):
    """Base class for agent tasks with tool support."""

    def __init__(self, flow_name: AvailableFlow):
        super().__init__(flow_name)
        self._tools_by_name: dict[str, BaseTool] = {}

    @property
    def input_schema(self) -> BaseGraphState:
        return BaseGraphState

    @property
    def state_schema(self) -> BaseGraphState:
        return BaseGraphState

    @property
    def output_schema(self) -> BaseGraphState:
        return BaseGraphState

    def get_tools(self) -> list[BaseTool]:
        """Return list of tools available to the agent."""
        return [TOOL_MAPPING[tool] for tool in self.config.tools]

    def build_system_prompt(self) -> list[ChatMessage]:
        """Builds system prompt from config."""
        return [
            ChatMessage(role=turn.side, content=turn.text)
            for turn in self.config.prompt_history
        ]

    def get_llm(self) -> BaseChatModel:
        """Get LLM bound to tools."""
        self._llm = super().get_llm()
        tools = self.get_tools()
        return self._llm.bind_tools(tools)

    def build_graph(self) -> StateGraph:
        """Build the agent graph with model and tool nodes."""
        # Setup tools
        tools = self.get_tools()
        self._tools_by_name = {tool.name: tool for tool in tools}

        # Create graph
        graph = StateGraph(self.state_schema)

        # node definitions
        def llm_node(state: BaseGraphState) -> BaseGraphState:
            """Calls LLM with message history and appends LLM response."""
            full_history = [*self._system_prompt, *state.messages]
            response = self._llm.invoke(full_history)
            return self.state_schema(messages=[*state.messages, response])

        def tool_node(state: BaseGraphState) -> BaseGraphState:
            """Checks if last message contains tool call and executes it."""
            last_message = state.messages[-1]
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return state

            tool_outputs = []
            for tool_call in last_message.tool_calls:
                logger.debug(
                    f"Task '{self.config.name}' executing tool call '{tool_call['name']}' with args={str(tool_call['args'])[:25]}..."  # noqa: E501
                )
                tool_result = self._tools_by_name[tool_call["name"]].invoke(
                    tool_call["args"]
                )
                tool_outputs.append(
                    ToolMessage(
                        content=json.dumps(tool_result)
                        if not isinstance(tool_result, str)
                        else tool_result,
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )
                logger.success(
                    f"Tool '{tool_call['name']}' responded with: '{tool_outputs[-1].content[:25]}...'"  # noqa: E501
                )
            return self.state_schema(messages=[*state.messages, *tool_outputs])

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
