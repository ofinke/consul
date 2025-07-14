# TODO: Add a factory which automatically creates mapping for config, can it even
# populate enum? is enum necessary if there will be factory for it?
# But in the end I would like tools to be handled by MCP.

from langchain_core.tools import tool


@tool
def get_weather(location: str) -> str:
    """Call to get the weather from a specific location."""
    if any(city in location.lower() for city in ["sf", "san francisco"]):
        return "It's sunny in San Francisco."
    return f"I am not sure what the weather is in {location}"
