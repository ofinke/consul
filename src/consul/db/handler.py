import functools

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

from consul.core.settings import settings


class DBHandler:
    """Database Handler for Consul operations."""

    def __init__(self) -> None:
        """Initializes engine to database."""
        self.engine = create_engine(settings.db_url)

        # Importing definitions of data models required to create table models.
        import consul.db.tables  # noqa: F401, PLC0415

        SQLModel.metadata.create_all(bind=self.engine)

    def store[T: BaseModel](self, data: list[T]) -> None:
        """Stores data of type[BaseModel] into corresponding table in database."""
        if not data:
            logger.debug("No data to store.")
            return

        with Session(self.engine) as session:
            try:
                for item in data:
                    session.add(item)
                session.commit()
            except Exception:
                session.rollback()
                raise
        logger.debug(f"Stored {len(data)} into '{data[0].__tablename__}' table.")

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


@functools.cache
def get_db_handler() -> DBHandler:
    """Return database handler."""
    return DBHandler()
