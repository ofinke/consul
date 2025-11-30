import functools
from typing import ClassVar

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy import update as sql_update
from sqlalchemy.sql import Select
from sqlmodel import Session, SQLModel, delete

from consul.core.schemas import MCPConfig
from consul.core.settings import settings

from .tables import AppConfigTable


class DBHandler:
    """Database Handler for Consul operations."""

    ConfigModelMap: ClassVar[dict[str | type[BaseModel]]] = {
        "MCPConfig": MCPConfig,
    }

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
                    statement = Select(data_schema)
                results = session.exec(statement)
                return list(results.all())
            except Exception:
                session.rollback()
                raise

    def load_config(self, name: str) -> BaseModel:
        """Loads configuration from AppConfigTable and return it's validated value."""
        with Session(self.engine) as session:
            try:
                stmt = Select(AppConfigTable).where(AppConfigTable.name == name)
                result = session.exec(stmt).first()[0]
            except Exception:
                session.rollback()
                raise

        if result is None:
            msg = f"Configuration with name '{name}' not found."
            logger.error(msg)
            raise ValueError(msg)

        model_cls = self.ConfigModelMap.get(result.validation_model)
        if model_cls is None:
            msg = f"Validation model '{result.validation_model}' not found in ConfigModelMap."
            logger.error(msg)
            raise ValueError(msg)

        return model_cls(**result.configuration)

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

    def clear_table[T: BaseModel](self, data_schema: type[T]) -> int:
        """Deletes all rows from the table corresponding to the given data_schema."""
        with Session(self.engine) as session:
            try:
                stmt = delete(data_schema)
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
