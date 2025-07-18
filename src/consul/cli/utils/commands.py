from pydantic import BaseModel, Field


class Commands(BaseModel):
    EXIT: list[str] = Field(default=["/q"], description="exit the application")
    SAVE: list[str] = Field(default=["/s"], description="save conversation history to markdown")
    RESET: list[str] = Field(default=["/r"], description="reset conversation history")
    FLOW: list[str] = Field(default=["/f"], description="change used flow and clear history")

    @classmethod
    def get_instructions(cls) -> str:
        return "; ".join(
            [
                f"To {cls.model_fields[command].description} write: {', '.join(cls.__pydantic_fields__[command].default)}"
                for command in cls.model_fields
            ]
        )
