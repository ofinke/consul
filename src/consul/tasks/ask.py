# TODO: redo this just for a simple ask a LLM task, which will be default entrypoint

from langchain_openai import AzureChatOpenAI

from consul.core.config.tasks import BaseTaskConfig
from consul.core.settings import settings
from consul.tasks.base import (
    BaseTaskInput,
    BaseTaskOutput,
    SimpleBaseTask,
)


class AskTask(SimpleBaseTask):
    """Ask LLM a question."""

    class Input(BaseTaskInput):
        """Task input data format."""

        text: str

    class Output(BaseTaskOutput):
        """Task output data format."""

    @property
    def config(self) -> BaseTaskConfig:
        return BaseTaskConfig(
            name="ask_question",
            description="Ask LLM a question.",
            tags=["question", "llm"],
        )

    @property
    def input_schema(self) -> BaseTaskInput:
        return self.Input

    @property
    def output_schema(self) -> BaseTaskOutput:
        return self.Output

    def create_prompt(self, state: dict[str, any]) -> str:
        text = state["text"]

        return f"Answer the following question:\n\n{text}\n\n"

    def get_llm(self):
        return AzureChatOpenAI(
            model=self.config.llm_name,
            **settings.azure.get_credentials(),
            **self.config.llm_params.model_dump()
        )

    def process_llm_response(
        self,
        response: str,
        _: dict[str, any],
    ) -> dict[str, any]:
        return {
            "llm_response": response.strip(),
        }
