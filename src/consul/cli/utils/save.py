import json
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, ChatMessage, ToolMessage
from loguru import logger


def _save_to_file(path: str, content: str) -> str:
    """Saves the content to a new file, creating directories if needed. Allowed suffixes: .md, .py."""
    # setup
    allowed_suffixes = [".md", ".py"]
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    # check if the file has allowed suffix.
    if suffix not in allowed_suffixes:
        msg = f"File '{file_path}' not created! Allowed file types: {', '.join(allowed_suffixes)}"
        logger.warning(msg)
        return msg

    # Create parent folders if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.exists():
        msg = f"File already exists: {file_path}"
        logger.error(msg)
        raise FileExistsError(msg)
    file_path.write_text(content, encoding="utf-8")
    return f"File created at {file_path!s}"


def _process_aimessage(turn: AIMessage, idx: int) -> str:
    out = [f"{idx}. **Assistant:**<br>→ "]
    if getattr(turn, "content", None):
        out.append(turn.content)
    elif getattr(turn, "tool_call", None):
        out.append("```json")
        out.append(json.dumps(turn.tool_call, indent=2))
        out.append("```")
    if hasattr(turn, "token_usage"):
        out.append(f"Tokens used: {turn.token_usage}")
    return "\n".join(out)


def _process_toolmessage(turn: ToolMessage, idx: int, preview_chars: int = 500) -> str:
    out = [f"{idx}. **Tool response:**<br>→"]
    content = getattr(turn, "content", "")
    if len(content) > preview_chars:
        out.append(content[:preview_chars] + "\n... (truncated)")
    else:
        out.append(content)
    if hasattr(turn, "token_usage"):
        out.append(f"Tokens used: {turn.token_usage}")
    return "\n".join(out)


def _process_chatmessage(turn: ChatMessage, idx: int) -> str:
    out = [f"{idx}. **User:**<br>→ ", turn.content]
    if hasattr(turn, "token_usage"):
        out.append(f"Tokens used: {turn.token_usage}")
    return "\n".join(out)


def save_memory(memory: list[BaseMessage]) -> str:
    text_to_save: list[str] = []

    for idx, turn in enumerate(memory, 1):
        if isinstance(turn, AIMessage):
            text_to_save.append(_process_aimessage(turn, idx))
        elif isinstance(turn, ToolMessage):
            text_to_save.append(_process_toolmessage(turn, idx))
        elif isinstance(turn, ChatMessage):
            text_to_save.append(_process_chatmessage(turn, idx))

    final_text = "\n\n".join(text_to_save)
    _save_to_file("history.md", final_text)
    return "history.md"
