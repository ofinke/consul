from abc import ABC, abstractmethod

from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from loguru import logger
from pydantic import BaseModel

from consul.core.config.base import ChatTurn
from consul.core.config.tasks import BaseTaskConfig


class BaseTaskInput(BaseModel):
    """Base input schema - tasks should subclass this."""


class BaseGraphState(BaseModel):
    """Base state of the langgraph graph."""

    history: list[ChatTurn]


class BaseTask(ABC):
    """Abstract base class for all tasks."""

    def __init__(self):
        self._graph: StateGraph | None = None
        self._compiled_graph = None

    # Core abstractions - must implement
    @property
    @abstractmethod
    def config(self) -> BaseTaskConfig:
        """Task metadata."""

    @property
    @abstractmethod
    def input_schema(self) -> BaseTaskInput:
        """Input schema for this task."""

    @property
    @abstractmethod
    def state_schema(self) -> BaseGraphState:
        """Output schema for task state."""

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Build the LangGraph graph for this task."""

    # Common interface
    def execute(self, input_data: dict[str, any]) -> BaseGraphState:
        """Execute the task with given input."""
        # inform about execution
        logger.info(f"Executing task: '{self.config.name}'")

        # Validate input
        validated_input = self.input_schema(**input_data)
        logger.debug(f"Task '{self.config.name}' {validated_input=}")

        # Get or build graph
        if self._compiled_graph is None:
            self._graph = self.build_graph()
            self._compiled_graph = self._graph.compile()
            logger.debug(f"Task '{self.config.name}' graph edges: {self._graph.edges}")
            logger.debug(f"Task '{self.config.name}' graph nodes: {self._graph.nodes}")

        # Execute
        result = self._compiled_graph.invoke(validated_input.dict())

        # return validated output
        return self.state_schema(**result)

    async def aexecute(self, input_data: dict[str, any]) -> BaseGraphState:
        """Async version of execute."""
        # inform about execution
        logger.info(f"Async executing task: '{self.config.name}'")

        # Validate input
        validated_input = self.input_schema(**input_data)
        logger.debug(f"Task '{self.config.name}' {validated_input=}")

        if self._compiled_graph is None:
            self._graph = self.build_graph()
            self._compiled_graph = self._graph.compile()
            logger.debug(f"Task '{self.config.name}' graph edges: {self._graph.edges}")
            logger.debug(f"Task '{self.config.name}' graph nodes: {self._graph.nodes}")

        # Execute
        result = await self._compiled_graph.ainvoke(validated_input.dict())

        # return validated output
        return self.state_schema(**result)


class SimpleBaseTask(BaseTask):
    """Base for simple single-pass LLM tasks."""

    @abstractmethod
    def create_prompt(self) -> ChatPromptTemplate:
        """Create the prompt for the LLM call."""

    @abstractmethod
    def get_llm(self):
        """Get the LLM instance to use."""

    def process_llm_response(
        self, response: str, state: BaseGraphState
    ) -> BaseGraphState:
        """Includes latest AI message in the BaseGraphState."""
        return BaseGraphState(
            history=[*state.history, ChatTurn(side="ai", text=response.strip())]
        )

    def build_graph(self) -> StateGraph:
        """Default graph: create prompt -> call LLM -> process the answer."""
        graph = StateGraph(self.state_schema)

        def llm_node(state: BaseGraphState) -> BaseGraphState:
            prompt = self.create_prompt(state)
            llm = self.get_llm()
            response = (prompt | llm).invoke({})
            return self.process_llm_response(response.content, state)

        graph.add_node("llm_call", llm_node)
        graph.set_entry_point("llm_call")
        graph.set_finish_point("llm_call")

        return graph
