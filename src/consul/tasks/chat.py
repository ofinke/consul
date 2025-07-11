from langchain.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from consul.core.config.tasks import (
    AvailableTasks,
    BaseTaskConfig,
    get_task_config,
)
from consul.core.settings import settings
from consul.tasks.base import (
    BaseGraphState,
    SimpleBaseTask,
)


class ChatTask(SimpleBaseTask):
    """Ask LLM a question."""

    class Input(BaseGraphState):
        """Task input data format."""

    @property
    def config(self) -> BaseTaskConfig:
        return get_task_config(AvailableTasks.CHAT)

    @property
    def input_schema(self) -> BaseGraphState:
        return self.Input

    @property
    def state_schema(self) -> BaseGraphState:
        return BaseGraphState

    def create_prompt(self, state: BaseGraphState) -> ChatPromptTemplate:
        config_history = [turn.dump_tuple() for turn in self.config.prompt_history]
        user_history = [turn.dump_tuple() for turn in state.history]
        return ChatPromptTemplate(config_history + user_history)

    def get_llm(self) -> AzureChatOpenAI:
        return AzureChatOpenAI(
            model=self.config.llm_name,
            **settings.azure.get_credentials(),
            **self.config.llm_params.model_dump(),
        )
