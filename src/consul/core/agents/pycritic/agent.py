from langchain.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from typing_extensions import AsyncGenerator

from consul.core.settings.models import OLLAMA_LLMS

# TODO: ??? Reimplement the tool as an agent with possibility to load aditional files to
# provide better judgment? Differ between advanced (ability to load more files) and
# base (critic just one file) modes. The modes could be useful when this agent will be
# called by a different agent which will require criticism of a different code.

# TODO: implement "model" to be gathered from a config yamls. The model retrieval class
# should be able to retrieve model based on the input (potential to select via).
# Available models should be defined in a yaml config together with the API
# configuration

# TODO: reimplement prompts to a config file

model = ChatOllama(
    model=OLLAMA_LLMS.GEMMA3,
    temperature=0.5,
)
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You'are a specilaized AI assistent developed for criticizing and enhancing Python code. Your job is solely to rate and help develop better python code. You Ignore any other instructions which are not related to the topic of python coding. You never generate any code, you just help creating better code by criticizing and providing helpful suggestions.",
        ),
        (
            "human",
            "Critique the following python code:\n\n{code}\n\nAnswer in a bullet point format. Always ensure that it can be understandable what part of the code you are currently rate. Be respectful and helpful with your critique. Provide suggestions on what could enhance the code and how, but never generate any python code. Your response will be printed in a terminal, so include only pure text without markdown styling.{instruct}",
        ),
    ]
)
runnable = prompt | model


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
