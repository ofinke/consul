from enum import Enum

from consul.tools.base import get_weather
from consul.tools.files import load_file, save_to_file
from consul.tools.find import find_patterns


class AvailableTools(Enum):
    WEATHER = "weather"
    LOAD_FILE = "load_file"
    SAVE_TO_FILE = "save_to_file"
    FIND_PATTERNS = "find_patterns"


TOOL_MAPPING = {
    AvailableTools.WEATHER: get_weather,
    AvailableTools.LOAD_FILE: load_file,
    AvailableTools.SAVE_TO_FILE: save_to_file,
    AvailableTools.FIND_PATTERNS: find_patterns,
}
