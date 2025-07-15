from abc import ABC, abstractmethod
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, ChatMessage
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph
from loguru import logger
from pydantic import BaseModel

from consul.core.config.flows import AvailableFlow, BaseFlowConfig, get_flow_config
from consul.core.settings import settings


class BaseFlowInput(BaseModel):
    """Base input schema - tasks should subclass this."""


class BaseGraphState(BaseModel):
    """Base state of the langgraph graph."""

    messages: Sequence[BaseMessage]


class BaseFlowOutput(BaseGraphState):
    """Base output schema - Use this for limit what output is presented to user."""


class BaseFlow(ABC):
    """Abstract base class for all tasks."""

    def __init__(self, flow_name: AvailableFlow) -> None:
        """
        Initialize the base flow for a task.

        Args:
            flow_name (AvailableFlow): The flow name specifying
                which flow/task to run and its associated configuration.

        Attributes:
            _flow_name (AvailableFlow): Stores the flow name.
            _system_prompt (list[ChatMessage]): Cached list of system prompt messages.
            _graph (StateGraph | None): LangGraph graph instance for the flow (uncompiled).
            _compiled_graph: Compiled LangGraph graph ready for execution.
            _llm (AzureChatOpenAI | None): The language model interface for LLM calls.

        """
        self._flow_name: AvailableFlow = flow_name
        self._system_prompt: list[ChatMessage] = []
        self._graph: StateGraph | None = None
        self._compiled_graph = None
        self._llm: AzureChatOpenAI | None = None

    @property
    def config(self) -> BaseFlowConfig:
        return get_flow_config(self._flow_name)

    # Core abstractions - must implement
    @property
    @abstractmethod
    def input_schema(self) -> BaseFlowInput:
        """Input schema for this task."""

    @property
    @abstractmethod
    def state_schema(self) -> BaseGraphState:
        """Schema used in the graph."""

    @property
    @abstractmethod
    def output_schema(self) -> BaseFlowOutput:
        """Output schema. Use if you want to limit what is returned to the user."""

    @abstractmethod
    def build_system_prompt(self) -> list[ChatMessage]:
        """Prepares the system prompt."""

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Build the LangGraph graph for this task."""

    # Common interface
    def get_llm(self) -> BaseChatModel:
        return AzureChatOpenAI(
            model=self.config.llm_name,
            **settings.azure.get_credentials(),
            **self.config.llm_params.model_dump(),
        )

    def prepare_to_run(self, input_data: dict[str, any]) -> BaseFlowInput:
        """
        Prepares the task to run by:
        - Validating input data.
        - Building system prompt if needed.
        - Instantiating the LLM interface if needed.
        - Compiling the graph if needed.

        Args:
            input_data: The raw input data for the task.

        Returns:
            validated_input: The validated and parsed input object.

        """
        # Validate input based on input schema
        validated_input = self.input_schema(**input_data)
        logger.debug(f"Task '{self.config.name}' {validated_input=}")

        # Build system prompt
        if not self._system_prompt:
            self._system_prompt = self.build_system_prompt()
            logger.debug(f"Task '{self.config.name}' {self._system_prompt=}")

        # Get the LLM model
        if not self._llm:
            self._llm = self.get_llm()
            logger.debug(f"Task '{self.config.name}' {self._llm=}")

        # Get or build graph
        if not self._compiled_graph:
            self._graph = self.build_graph()
            self._compiled_graph = self._graph.compile()
            logger.debug(f"Task '{self.config.name}' graph edges: {self._graph.edges}")
            logger.debug(f"Task '{self.config.name}' graph nodes: {self._graph.nodes}")

        return validated_input

    def execute(self, input_data: dict[str, any]) -> BaseGraphState:
        """Execute the task with given input."""
        validated_input = self.prepare_to_run(input_data)
        result = self._compiled_graph.invoke(validated_input)
        return self.state_schema(**result)

    # TODO: write full async implementation
    # async def aexecute(self, input_data: dict[str, any]) -> BaseGraphState:
    #     """Async version of execute."""
    #     logger.info(f"Async executing task: '{self.config.name}'")
    #     validated_input = self.prepare_to_run(input_data)
    #     result = await self._compiled_graph.ainvoke(validated_input)
    #     return self.state_schema(**result)
