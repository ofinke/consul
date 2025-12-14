from typing import Any

from loguru import logger


class Registry:
    """Default class for defining different registiries across the app."""

    def __init__(self) -> None:
        """Initializes class with empty entries."""
        self.entries: dict[str, Any] = {}

    def register(self, name: str, value: Any) -> None:
        """Register value as a registry entry."""
        self.entries[name] = value

    def get[T](self, name: str) -> T:
        """Returns registered value or raises exception if the value is not available."""
        try:
            return self.entries[name]
        except KeyError as e:
            msg = f"Registry '{self.__class__}' doesn't contain entry tied to '{name}'."
            logger.warning(msg)
            raise KeyError(msg) from e

    def get_all[T](self) -> list[T]:
        """Returns all registered items as a list."""
        return list(self.entries.values())

    def get_all_keys(self) -> list[str]:
        """Return all available keys as a list."""
        return list(self.entries.keys())
