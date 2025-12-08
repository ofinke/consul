from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage, ChatMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph
from loguru import logger

from consul.core.schemas import FlowConfig
from consul.prompts.registry import get_prompt_registry

from .base import BaseFlow, BaseGraphState
from .log import LoggingHandler


class SummaryTask(BaseFlow):
    """
    Task designed to summarize previous chat history.

    As an input, takes the whole input history and merges it as a single message divided into human messages, tool
    responses and ai messages. Graph steps:
        1. Merge history into a single human message
        2. Call LLM
    """

    def __init__(self, flow_config: FlowConfig) -> None:
        """Init including the logging handler."""
        super().__init__(flow_config)
        self.logging = LoggingHandler()

    @property
    def input_schema(self) -> BaseGraphState:
        return BaseGraphState

    @property
    def state_schema(self) -> BaseGraphState:
        return BaseGraphState

    def build_system_prompt(self) -> list[ChatMessage]:
        """
        Loads system prompt.

        Takes into account only 'system' side and ignores rest. Warns user, when unsupported system prompt is passed.
        """
        sysprompt = []
        for turn in self.config.prompt_history:
            if turn.side != "system":
                logger.warning(
                    f"{self.__class__.__name__} doesn't support starting prompt with side {turn.side}. Skipping"
                )
                continue
            sysprompt.append(ChatMessage(role=turn.side, content=turn.text.format_map(get_prompt_registry().entries)))
        return sysprompt

    async def build_graph(self) -> StateGraph:
        """Default graph: create prompt -> call LLM -> process the answer."""
        graph = StateGraph(self.state_schema)

        def merge_history(state: BaseGraphState) -> BaseGraphState:
            """Takes chat history and merge it into a single message."""
            text = ""
            for message in state.messages:
                if isinstance(message, HumanMessage):
                    text += f"==== Human Message ====\n```text{message.text}```\n\n"
                    continue
                if isinstance(message, AIMessage):
                    text += f"==== AI Message ====\n```text{message.text}```\n\n"
                    continue
                if isinstance(message, ToolMessage):
                    text += f"==== Tool Reply ====\n```text{message.text}```\n\n"
                    continue

                logger.warning(f"Unknown messages type: {type(message)} occured.")

            state.messages = [HumanMessage(content=text)]
            return state

        def llm_node(state: BaseGraphState) -> BaseGraphState:
            """Logs user message, calls LLM, logs LLM answer, and appends LLM response to chat history."""
            full_history = [*self._system_prompt, *state.messages]
            self.logging.log_message(self.state_schema(messages=full_history, **state.model_dump(exclude="messages")))
            response = self._llm.invoke(full_history)
            new_state = self.state_schema(messages=[*state.messages, response], **state.model_dump(exclude="messages"))
            self.logging.log_message(new_state)
            return new_state

        # Define the graph

        graph.add_node(merge_history.__name__, merge_history)
        graph.add_node(llm_node.__name__, llm_node)

        graph.add_edge(merge_history.__name__, llm_node.__name__)

        graph.set_entry_point(merge_history.__name__)
        graph.set_finish_point(llm_node.__name__)

        return graph
