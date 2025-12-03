import functools
from typing import ClassVar

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy import update as sql_update
from sqlalchemy.sql import Select
from sqlmodel import Session, SQLModel, delete

from consul.core.schemas import FlowConfig, MCPConfig
from consul.core.settings import settings

from .tables import AppConfigTable


class DBHandler:
    """Database Handler for Consul operations."""

    ConfigModelMap: ClassVar[dict[str | type[BaseModel]]] = {
        "MCPConfig": MCPConfig,
        "FlowConfig": FlowConfig,
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

    def load_config(self, *, name: str | None = None, data_schema: str | None = None) -> list[BaseModel]:
        """
        Loads one or more configurations from AppConfigTable.

        - If 'name' is provided → load a single configuration by name.
        - If 'name' is not provided → 'data_schema' must be provided, loads all of that schema.
        """
        if not name and not data_schema:
            msg = "Either 'name' or 'data_schema' must be provided."
            logger.error(msg)
            raise ValueError(msg)

        with Session(self.engine) as session:
            try:
                # Build query conditionally
                if name:
                    statement = Select(AppConfigTable).where(AppConfigTable.name == name)
                else:
                    statement = Select(AppConfigTable).where(AppConfigTable.validation_model == data_schema)
                # TODO: session.exec(statement).all() returns tuple instead of just data, why?
                results = [row[0] for row in session.exec(statement).all()]
            except Exception:
                session.rollback()
                raise

        if not results:
            msg = f"Didn't retrieve any configuration based on {name=} and {data_schema}"
            logger.error(msg)
            raise ValueError(msg)

        # Resolve which validation model to use
        model_cls = self.ConfigModelMap.get(results[0].validation_model)
        if model_cls is None:
            msg = f"Validation model '{results[0].validation_model}' not found in ConfigModelMap."
            logger.error(msg)
            raise ValueError(msg)

        return [model_cls(**r.configuration) for r in results]

    def update[T: BaseModel](self, model: type[T], filters: dict[str, object], update_values: dict[str, object]) -> int:
        """Update rows in the table that match given filters with provided values."""
        with Session(self.engine) as session:
            try:
                statement = sql_update(model).filter_by(**filters).values(**update_values)
                result = session.exec(statement)
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
                statement = delete(data_schema)
                result = session.exec(statement)
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
