from langchain_core.messages import ChatMessage
from langchain_core.tools import tool

from consul.flow.agents.base import BaseAgentFlow


@tool
def get_weather(location: str) -> str:
    """Call to get the weather from a specific location."""
    if any(city in location.lower() for city in ["sf", "san francisco"]):
        return "It's sunny in San Francisco."
    return f"I am not sure what the weather is in {location}"


class ReactAgentTask(BaseAgentFlow):
    """ReAct agent that can use tools to answer questions."""

    def get_tools(self) -> list:
        """Return available tools for the agent."""
        return [get_weather]

    def build_system_prompt(self) -> list[ChatMessage]:
        return [
            ChatMessage(role=turn.side, content=turn.text)
            for turn in self.config.prompt_history
        ]
