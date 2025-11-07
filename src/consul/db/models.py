from datetime import UTC, datetime

from sqlmodel import DateTime, Field, SQLModel, func


class BaseTableModel(SQLModel, table=False):
    """
    Base table definition.
    All database tables in consul should inherit this model.
    """

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


class MessageLogModel(BaseTableModel, table=True):
    """Data model for automatic message logging."""

    cid: str
    flow: str
    author: str
    message: str
    metadata: str
