import functools

from pydantic import BaseModel
from sqlalchemy import create_engine

from consul.core.settings import settings


class DBHandler:
    """Database Handler for Consul operations."""

    def __init__(self) -> None:
        """Initializes engine to database."""
        self.engine = create_engine(settings.db_url)

    def store[T: BaseModel](self, data: list[T]) -> None:
        """Stores data of type[BaseModel] into corresponding table in database."""
        raise NotImplementedError

    def load[T: BaseModel](self, data_schema: T) -> None:
        """Loads whole table based on its definition."""
        raise NotImplementedError


@functools.cache()
def get_db_handler() -> DBHandler:
    msg = "Not yet"
    raise NotImplementedError(msg)
