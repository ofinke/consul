import functools

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy import update as sql_update
from sqlalchemy.sql import Select
from sqlmodel import Session, SQLModel

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

    def load[T: BaseModel](self, data_schema: type[T], *, statement: Select | None = None) -> list[T]:
        """Loads data from the table using a provided SQLAlchemy statement or defaults to full table."""
        with Session(self.engine) as session:
            try:
                if statement is None:
                    statement = statement(data_schema)
                results = session.exec(statement)
                return list(results.all())
            except Exception:
                session.rollback()
                raise

    def update[T: BaseModel](self, model: type[T], filters: dict[str, object], update_values: dict[str, object]) -> int:
        """Update rows in the table that match given filters with provided values."""
        with Session(self.engine) as session:
            try:
                stmt = sql_update(model).filter_by(**filters).values(**update_values)
                result = session.exec(stmt)
                session.commit()
            except Exception:
                session.rollback()
                raise
            else:
                return result.rowcount if result else 0


@functools.cache
def get_db_handler() -> DBHandler:
    """Return database handler."""
    return DBHandler()
