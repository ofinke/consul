import functools

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlmodel import Session, select

from consul.core.settings import settings


class DBHandler:
    """Database Handler for Consul operations."""

    def __init__(self) -> None:
        """Initializes engine to database."""
        self.engine = create_engine(settings.db_url)

    def store[T: BaseModel](self, data: list[T]) -> None:
        """Stores data of type[BaseModel] into corresponding table in database."""
        if not data:
            return

        with Session(self.engine) as session:
            try:
                for item in data:
                    session.add(item)
                session.commit()
            except Exception:
                session.rollback()
                raise

    def load[T: BaseModel](self, data_schema: type[T]) -> list[T]:
        """Loads whole table based on its definition."""
        with Session(self.engine) as session:
            try:
                statement = select(data_schema)
                results = session.exec(statement)
                return list(results.all())
            except Exception:
                session.rollback()
                raise


@functools.cache()
def get_db_handler() -> DBHandler:
    msg = "Not yet"
    raise NotImplementedError(msg)
