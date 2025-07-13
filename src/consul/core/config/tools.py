from enum import Enum

from consul.tools.base import get_weather


class AvailableTools(Enum):
    WEATHER = "weather"


TOOL_MAPPING = {
    AvailableTools.WEATHER: get_weather,
}
