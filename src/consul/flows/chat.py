from langchain_core.messages import ChatMessage
from langgraph.graph import StateGraph

from consul.core.config.flows import AvailableFlow
from consul.core.config.prompts import PROMPT_FORMAT_MAPPING
from consul.flows.base import BaseFlow, BaseGraphState
from consul.flows.logging import LoggingHandler


class ChatTask(BaseFlow):
    """Ask LLM a question."""

    def __init__(self, flow_name: AvailableFlow) -> None:
        """Init including the logging handler."""
        super().__init__(flow_name)
        self.logging = LoggingHandler()

    @property
    def input_schema(self) -> BaseGraphState:
        return BaseGraphState

    @property
    def state_schema(self) -> BaseGraphState:
        return BaseGraphState

    def build_system_prompt(self) -> list[ChatMessage]:
        return [
            ChatMessage(role=turn.side, content=turn.text.format_map(PROMPT_FORMAT_MAPPING))
            for turn in self.config.prompt_history
        ]

    def build_graph(self) -> StateGraph:
        """Default graph: create prompt -> call LLM -> process the answer."""
        graph = StateGraph(self.state_schema)

        def llm_node(state: BaseGraphState) -> BaseGraphState:
            """Logs user message, calls LLM, logs LLM answer, and appends LLM response to chat history."""
            full_history = [*self._system_prompt, *state.messages]
            self.logging.log_message(self.state_schema(messages=full_history, **state.model_dump(exclude="messages")))
            response = self._llm.invoke(full_history)
            new_state = self.state_schema(messages=[*state.messages, response], **state.model_dump(exclude="messages"))
            self.logging.log_message(new_state)
            return new_state

        graph.add_node("llm_call", llm_node)
        graph.set_entry_point("llm_call")
        graph.set_finish_point("llm_call")

        return graph
