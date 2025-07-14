from enum import Enum

from consul.tools.base import get_weather
from consul.tools.files import load_file, save_to_markdown


class AvailableTools(Enum):
    WEATHER = "weather"
    LOAD_FILE = "load_file"
    SAVE_TO_MARKDOWN = "save_to_markdown"


TOOL_MAPPING = {
    AvailableTools.WEATHER: get_weather,
    AvailableTools.LOAD_FILE: load_file,
    AvailableTools.SAVE_TO_MARKDOWN: save_to_markdown,
}
