from abc import ABC, abstractmethod

from langgraph.graph import StateGraph
from loguru import logger
from pydantic import BaseModel


class BaseTaskInput(BaseModel):
    """Base input schema - tasks should subclass this."""


class BaseTaskOutput(BaseModel):
    """Base output schema - tasks should subclass this."""
    llm_response: str


class BaseTaskMetadata(BaseModel):
    """Metadata about the task."""

    name: str
    description: str
    version: str = "0.0.0"
    tags: list[str] = []
    timeout_seconds: int | None = None


class BaseTask(ABC):
    """Abstract base class for all tasks."""

    def __init__(self):
        self._graph: StateGraph | None = None
        self._compiled_graph = None

    # Core abstractions - must implement
    @property
    @abstractmethod
    def metadata(self) -> BaseTaskMetadata:
        """Task metadata."""

    @property
    @abstractmethod
    def input_schema(self) -> BaseTaskInput:
        """Input schema for this task."""

    @property
    @abstractmethod
    def output_schema(self) -> BaseTaskOutput:
        """Output schema for this task."""

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Build the LangGraph graph for this task."""

    # Common interface
    def execute(self, input_data: dict[str, any]) -> BaseTaskOutput:
        """Execute the task with given input."""
        # inform about execution
        logger.info(f"Executing task: '{self.metadata.name}'")

        # Validate input
        validated_input = self.input_schema(**input_data)
        logger.debug(f"Task '{self.metadata.name}' input {validated_input=}")

        # Get or build graph
        if self._compiled_graph is None:
            self._graph = self.build_graph()
            self._compiled_graph = self._graph.compile()
            logger.debug(f"Task '{self.metadata.name}' graph edges: {self._graph.edges}")
            logger.debug(f"Task '{self.metadata.name}' graph nodes: {self._graph.nodes}")

        # Execute
        result = self._compiled_graph.invoke(validated_input.dict())
        logger.debug(f"Task '{self.metadata.name}' graph result: {result}")

        # return validated output
        return self.output_schema(**result)

    async def aexecute(self, input_data: dict[str, any]) -> BaseTaskOutput:
        """Async version of execute."""
        logger.info(f"Async executing task: '{self.metadata.name}'")
        validated_input = self.input_schema(**input_data)

        if self._compiled_graph is None:
            self._graph = self.build_graph()
            self._compiled_graph = self._graph.compile()
            logger.debug(f"Task '{self.metadata.name}' graph edges: {self._graph.edges}")
            logger.debug(f"Task '{self.metadata.name}' graph nodes: {self._graph.nodes}")

        result = await self._compiled_graph.ainvoke(validated_input.dict())
        logger.debug(f"Task '{self.metadata.name}' graph result: {result}")

        return self.output_schema(**result)


class SimpleBaseTask(BaseTask):
    """Base for simple single-pass LLM tasks."""

    @abstractmethod
    def create_prompt(self, state: dict[str, any]) -> str:
        """Create the prompt for the LLM call."""

    @abstractmethod
    def get_llm(self):
        """Get the LLM instance to use."""

    def process_llm_response(
        self, response: str, state: dict[str, any]
    ) -> dict[str, any]:
        """Process LLM response - override if needed."""
        state["llm_response"] = response
        return state

    def build_graph(self) -> StateGraph:
        """Default graph: prompt -> LLM -> process."""
        graph = StateGraph(dict)

        def llm_node(state):
            prompt = self.create_prompt(state)
            llm = self.get_llm()
            response = llm.invoke(prompt)
            return self.process_llm_response(response.content, state)

        graph.add_node("llm_call", llm_node)
        graph.set_entry_point("llm_call")
        graph.set_finish_point("llm_call")

        return graph
