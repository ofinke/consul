from langchain_core.prompts import ChatPromptTemplate

from consul.core.schemas.agents import BaseAgentConfig


def create_chat_prompts(agent: BaseAgentConfig) -> str:
    prompt_history_list = [(turn.side, turn.text) for turn in agent.prompt_history]
    return ChatPromptTemplate.from_messages(prompt_history_list)
