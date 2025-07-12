import json
from abc import abstractmethod
from collections.abc import Sequence
from typing import Annotated, Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from consul.core.config.flow import AvailableFlow
from consul.flow.base import BaseFlow, BaseGraphState


class AgentGraphState(BaseGraphState):
    """State that includes LangChain messages for tool handling."""

    messages: Sequence[BaseMessage]


class BaseAgentFlow(BaseFlow):
    """Base class for agent tasks with tool support."""

    def __init__(self, config: AvailableFlow):
        super().__init__(config)
        self._tools_by_name: dict[str, BaseTool] = {}

    @property
    def input_schema(self) -> BaseGraphState:
        return BaseGraphState

    @property
    def state_schema(self) -> AgentGraphState:
        return AgentGraphState

    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """Return list of tools available to the agent."""

    def get_llm(self):
        """Get LLM bound to tools."""
        self._llm = super().get_llm()
        tools = self.get_tools()
        return self._llm.bind_tools(tools)

    def should_continue(self, state: AgentGraphState) -> str:
        """Determine if agent should continue or end."""
        if not state.messages:
            return "end"

        last_message = state.messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        return "end"

    def tool_node(self, state: AgentGraphState) -> AgentGraphState:
        """Node that executes tools."""
        if not state.messages:
            return {"messages": []}

        last_message = state.messages[-1]
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        outputs = []
        for tool_call in last_message.tool_calls:
            tool_result = self._tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result)
                    if not isinstance(tool_result, str)
                    else tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": [*state.messages, *outputs]}

    def build_graph(self) -> StateGraph:
        """Build the agent graph with model and tool nodes."""
        # Setup tools
        tools = self.get_tools()
        self._tools_by_name = {tool.name: tool for tool in tools}

        # Create graph
        graph = StateGraph(self.state_schema)

        # node definitions
        def llm_node(state: AgentGraphState) -> AgentGraphState:
            full_history = [*self._system_prompt, *state.messages]
            response = self._llm.invoke(full_history)
            return self.append_llm_response(response, state)

        def tool_node(state: AgentGraphState) -> AgentGraphState:
            pass


        # Add nodes
        graph.add_node("agent", llm_node)
        graph.add_node("tools", self.tool_node)

        # Set entry point
        graph.set_entry_point("agent")

        # Add conditional edges
        graph.add_conditional_edges(
            "agent",
            self.should_continue,
            {
                "continue": "tools",
                "end": END,
            },
        )

        # Add edge from tools back to agent
        graph.add_edge("tools", "agent")

        return graph

    def append_llm_response(
        self, response: AIMessage, state: AgentGraphState
    ) -> AgentGraphState:
        """Includes latest AI message in the BaseGraphState."""
        return AgentGraphState(messages=[*state.messages, response])

    # def execute(self, input_data: dict[str, any]) -> AgentGraphState:
    #     """Override to handle message conversion."""
    #     # Convert input message to LangChain format
    #     if "message" in input_data:
    #         from langchain_core.messages import HumanMessage

    #         input_data["messages"] = [HumanMessage(content=input_data["message"])]

    #     result = super().execute(input_data)

    #     # Update history for compatibility
    #     result.history = result.to_chat_turns()

    #     return result
