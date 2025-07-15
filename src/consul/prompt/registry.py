import importlib
import os

from loguru import logger

# registry.py
registry = {}


def autodiscover_plugins():
    current_dir = os.path.dirname(__file__)  # <== /prompt
    logger.info(current_dir)
    for fname in os.listdir(current_dir):
        if (
            fname.endswith(".py")
            and fname != "registry.py"
            and not fname.startswith("__")
        ):
            module_name = f"{__package__}.{fname[:-3]}" if __package__ else fname[:-3]
            importlib.import_module(module_name)


def register(func):
    registry[func.__name__] = func
    return func


# Discover and register all plugins at import time:
autodiscover_plugins()