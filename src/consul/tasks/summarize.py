# TODO: redo this just for a simple ask a LLM task, which will be default entrypoint

from langchain_openai import AzureChatOpenAI

from consul.core.settings import settings
from consul.tasks.base import SimpleBaseTask, TaskInput, TaskMetadata, TaskOutput


class SummarizeTextTask(SimpleBaseTask):
    """Summarize text with optional length constraint."""

    class Input(TaskInput):
        """Task input data format."""

        text: str
        max_length: int | None = None

    class Output(TaskOutput):
        """Task output data format."""

        summary: str
        original_length: int
        summary_length: int

    @property
    def metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="summarize_text",
            description="Summarizes input text to specified length",
            tags=["text", "summarization", "llm"],
        )

    @property
    def input_schema(self) -> TaskInput:
        return self.Input

    @property
    def output_schema(self) -> TaskOutput:
        return self.Output

    def create_prompt(self, state: dict[str, any]) -> str:
        text = state["text"]
        max_length = state.get("max_length")

        prompt = f"Summarize the following text:\n\n{text}\n\n"
        if max_length:
            prompt += f"Keep the summary under {max_length} characters."

        return prompt

    def get_llm(self):
        return AzureChatOpenAI(model="gpt-4.1", **settings.azure.get_credentials())

    def process_llm_response(
        self, response: str, state: dict[str, any]
    ) -> dict[str, any]:
        return {
            "summary": response.strip(),
            "original_length": len(state["text"]),
            "summary_length": len(response.strip()),
        }
