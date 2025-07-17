from enum import Enum

from consul.tools.base import get_weather
from consul.tools.files import load_file, save_to_file


class AvailableTools(Enum):
    WEATHER = "weather"
    LOAD_FILE = "load_file"
    SAVE_TO_FILE = "save_to_file"


TOOL_MAPPING = {
    AvailableTools.WEATHER: get_weather,
    AvailableTools.LOAD_FILE: load_file,
    AvailableTools.SAVE_TO_FILE: save_to_file,
}
