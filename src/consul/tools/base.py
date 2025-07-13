from langchain_core.tools import tool


@tool
def get_weather(location: str) -> str:
    """Call to get the weather from a specific location."""
    if any(city in location.lower() for city in ["sf", "san francisco"]):
        return "It's sunny in San Francisco."
    return f"I am not sure what the weather is in {location}"
