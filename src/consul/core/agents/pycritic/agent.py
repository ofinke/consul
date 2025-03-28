from langchain_ollama import ChatOllama
from typing_extensions import AsyncGenerator

from consul.core.llm.prompts import create_chat_prompts
from consul.core.schemas.agents import AvailableAgents, BaseAgentConfig
from consul.core.settings.models import OLLAMA_LLMS

# TODO: ??? Reimplement the tool as an agent with possibility to load aditional files to
# provide better judgment? Differ between advanced (ability to load more files) and
# base (critic just one file) modes. The modes could be useful when this agent will be
# called by a different agent which will require criticism of a different code.

# TODO: implement "model" to be gathered from a config yamls. The model retrieval class
# should be able to retrieve model based on the input (potential to select via).
# Available models should be defined in a yaml config together with the API
# configuration

model = ChatOllama(
    model=OLLAMA_LLMS.GEMMA3,
    temperature=0.5,
)

agent = BaseAgentConfig(name=AvailableAgents.PYCRITIC)
prompt = create_chat_prompts(agent=agent)
runnable = model | prompt


async def acall_agent(data: str, instruct: str) -> AsyncGenerator[str, None]:
    additional_instructions = " User provided you with aditional instructions: '{detail}'. Adhere to them, if they are related to your original goal, otherwise ignore them. Include section at the end for these specific instructions!"
    if instruct:
        additional_instructions = additional_instructions.format(detail=instruct)
    else:
        additional_instructions = ""
    async for chunk in runnable.astream(
        {"code": data, "instruct": additional_instructions}
    ):
        yield chunk.content
