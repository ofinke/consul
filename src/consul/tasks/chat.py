from langchain.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from consul.core.config.tasks import (
    AvailableTasks,
    BaseTaskConfig,
    ChatTurn,
    get_task_config,
)
from consul.core.settings import settings
from consul.tasks.base import (
    BaseTaskInput,
    BaseTaskOutput,
    SimpleBaseTask,
)


class ChatTask(SimpleBaseTask):
    """Ask LLM a question."""

    class Input(BaseTaskInput):
        """Task input data format."""

        history: list[ChatTurn]

    class Output(BaseTaskOutput):
        """Task output data format."""

    @property
    def config(self) -> BaseTaskConfig:
        return get_task_config(AvailableTasks.CHAT)

    @property
    def input_schema(self) -> BaseTaskInput:
        return self.Input

    @property
    def output_schema(self) -> BaseTaskOutput:
        return self.Output

    def create_prompt_history(self, state: dict[str, any]) -> ChatPromptTemplate:
        config_history = [turn.dump_tuple() for turn in self.config.prompt_history]
        user_history = [(turn["side"], turn["text"]) for turn in state["history"]]
        return ChatPromptTemplate(config_history + user_history)

    def get_llm(self):
        return AzureChatOpenAI(
            model=self.config.llm_name,
            **settings.azure.get_credentials(),
            **self.config.llm_params.model_dump(),
        )

    def process_llm_response(
        self,
        response: str,
        state: dict[str, any],
    ) -> list[ChatTurn]:
        user_history = [ChatTurn(**turn) for turn in state["history"]]
        return {
            "history": [*user_history, ChatTurn(side="ai", text=response.strip())]
        }
