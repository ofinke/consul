from langchain_core.messages import ChatMessage
from langgraph.graph import StateGraph

from consul.core.config.prompts import PROMPT_FORMAT_MAPPING
from consul.flows.base import BaseFlow, BaseGraphState


class ChatTask(BaseFlow):
    """Ask LLM a question."""

    @property
    def input_schema(self) -> BaseGraphState:
        return BaseGraphState

    @property
    def state_schema(self) -> BaseGraphState:
        return BaseGraphState

    @property
    def output_schema(self) -> BaseGraphState:
        return BaseGraphState

    def build_system_prompt(self) -> list[ChatMessage]:
        return [
            ChatMessage(
                role=turn.side,
                content=turn.text.format_map(PROMPT_FORMAT_MAPPING),
            )
            for turn in self.config.prompt_history
        ]

    def build_graph(self) -> StateGraph:
        """Default graph: create prompt -> call LLM -> process the answer."""
        graph = StateGraph(self.state_schema)

        def llm_node(state: BaseGraphState) -> BaseGraphState:
            full_history = [*self._system_prompt, *state.messages]
            response = self._llm.invoke(full_history)
            return self.state_schema(messages=[*state.messages, response])

        graph.add_node("llm_call", llm_node)
        graph.set_entry_point("llm_call")
        graph.set_finish_point("llm_call")

        return graph
