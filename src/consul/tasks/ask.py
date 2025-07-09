# TODO: redo this just for a simple ask a LLM task, which will be default entrypoint

from langchain_openai import AzureChatOpenAI

from consul.core.settings import settings
from consul.tasks.base import (
    BaseTaskInput,
    BaseTaskMetadata,
    BaseTaskOutput,
    SimpleBaseTask,
)


class AskTask(SimpleBaseTask):
    """Ask LLM a question."""

    class Input(BaseTaskInput):
        """Task input data format."""

        text: str
        max_length: int | None = None

    class Output(BaseTaskOutput):
        """Task output data format."""

    @property
    def metadata(self) -> BaseTaskMetadata:
        return BaseTaskMetadata(
            name="ask_question",
            description="Ask a question to a LLM.",
            tags=["text", "question", "llm"],
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
        return AzureChatOpenAI(model="gpt-4.1", **settings.azure.get_credentials())

    def process_llm_response(
        self, response: str, state: dict[str, any]
    ) -> dict[str, any]:
        return {
            "llm_response": response.strip(),
        }
