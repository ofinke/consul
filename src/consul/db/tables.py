from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Text
from sqlalchemy.types import JSON
from sqlmodel import DateTime, Field, SQLModel, func


class BaseTable(SQLModel, table=False):
    """
    Base table definition.
    All database tables in consul should inherit this model.
    """

    # TODO: Think about the ID options as I'm using the ID to retrieve data, is there some equivalent which allows me
    # to store more data for example in 4 signs? some hexadecimal or other? Goal is to have as much row with ids < 5
    # letters. Use the the ID 183 conversation from my work DB by writing base36encode, decode utils
    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"comment": "Item ID"},
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "comment": "The timestamp when the item was created",
            "server_default": func.now(),
        },
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={
            "comment": "The timestamp when the item was updated",
            "server_default": func.now(),
            "onupdate": func.now(),
        },
    )


class MessageLogTable(BaseTable, table=True):
    """Data model for automatic message logging."""

    __tablename__ = "log_messages"

    # Identificators
    cid: str = Field(
        max_length=64,
        nullable=False,
        index=True,
        sa_column_kwargs={"comment": "Conversation ID"},
    )
    flow: str = Field(
        max_length=64,
        nullable=False,
        index=True,
        sa_column_kwargs={"comment": "Flow name"},
    )
    author: str = Field(
        max_length=64,
        nullable=False,
        index=True,
        sa_column_kwargs={"comment": "Message author"},
    )
    # Values
    message: str = Field(
        sa_type=Text,
        nullable=False,
        sa_column_kwargs={"comment": "Message content"},
    )
    tool_call: list[dict[str, Any]] = Field(
        default_factory=list,
        nullable=True,
        sa_type=JSON,
        sa_column_kwargs={"comment": "Tool calls invoked"},
    )
    tool_call_id: str = Field(
        max_length=64,
        nullable=True,
        sa_column_kwargs={"comment": "Tool call ID connected to Tool Message"},
    )
    llm: str = Field(
        max_length=64,
        nullable=True,
        sa_column_kwargs={"comment": "LLM model used"},
    )
    usage_metadata: dict[str, Any] = Field(
        default_factory=dict,
        nullable=True,
        sa_type=JSON,
        sa_column_kwargs={"comment": "Usage metadata"},
    )
    # Archive keys
    summary: str = Field(
        sa_type=Text,
        nullable=True,
        sa_column_kwargs={"comment": "LLM based summary for archived conversations"},
    )
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        nullable=True,
        sa_type=JSON,
        sa_column_kwargs={"comment": "Custom metadata stored for archived conversations"},
    )


# class FlowConfigTable(BaseTable, table=False):
#     """Preparation for implementing flows definitions into database."""

#     __tablename__ = "flow_configs"

#     # LLM definition
#     llm_name: str
#     llm_params: dict[str, Any]

#     # tools definition
#     tools: None

#     # prompt
