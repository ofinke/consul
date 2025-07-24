import json
from datetime import datetime
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, ChatMessage, ToolMessage
from loguru import logger


def _save_to_markdown(path: str, content: str) -> None:
    """Saves the content to a markdown, creating directories if needed."""
    # setup
    file_path = Path(path)

    # Create parent folders if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.exists():
        msg = f"File already exists: {file_path}"
        logger.error(msg)
        raise FileExistsError(msg)
    file_path.write_text(content, encoding="utf-8")


def _truncate_strings(obj: dict | list | str, max_length: str = 500) -> dict | list | str:
    """Limiter for output size."""
    if isinstance(obj, dict):
        return {k: _truncate_strings(v, max_length) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_truncate_strings(i, max_length) for i in obj]
    if isinstance(obj, str):
        if len(obj) > max_length:
            return obj[:max_length] + "(...truncated)"
        return obj
    return obj


def _process_aimessage(turn: AIMessage, idx: int) -> str:
    """Convert content of AIMessage into a markdown string."""
    out = [f"## {idx}) Assistant:\n\n"]
    # load message content
    if turn.content:
        out.append(f"→ {turn.content}")
    # load tool calls
    if "tool_calls" in turn.additional_kwargs:
        truncated = _truncate_strings(turn.additional_kwargs["tool_calls"])
        out.append("\n\nAssistant tool calls:")
        out.append("```json")
        out.append(json.dumps(truncated, indent=4))
        out.append("```")
    # load token usage
    if turn.usage_metadata:
        out.append(
            f"→ Input tokens: {turn.usage_metadata['input_tokens']}, Output tokens: {turn.usage_metadata['output_tokens']}"  # noqa: E501
        )
    return "\n\n".join(out)


def _process_toolmessage(turn: ToolMessage, idx: int) -> str:
    """Convert content of ToolMessage into a markdown string."""
    out = [f"## {idx}) Tool response:\n\n"]
    keys_order = ["name", "tool_call_id", "status", "content"]
    truncated = _truncate_strings(turn.model_dump(include=keys_order))
    # dump ordered dict
    out.append("```json")
    out.append(json.dumps({k: truncated[k] for k in keys_order if k in truncated}, indent=4))
    out.append("```")
    return "\n".join(out)


def _process_chatmessage(turn: ChatMessage, idx: int) -> str:
    """Convert content of ChatMessage into a markdown string."""
    out = [f"## {idx}) User:\n\n→ ", turn.content]
    if hasattr(turn, "token_usage"):
        out.append(f"Tokens used: {turn.token_usage}")
    return "\n".join(out)


def save_memory(history: list[BaseMessage], flow_name: str) -> str:
    """Save conversation history into a markdown file."""
    # process the history
    text_to_save: list[str] = []
    for idx, turn in enumerate(history):
        turn_id = idx + 1
        if isinstance(turn, AIMessage):
            text_to_save.append(_process_aimessage(turn, turn_id))
        elif isinstance(turn, ToolMessage):
            text_to_save.append(_process_toolmessage(turn, turn_id))
        elif isinstance(turn, ChatMessage):
            text_to_save.append(_process_chatmessage(turn, turn_id))
    # finalize and save
    final_text = "\n\n---\n\n".join(text_to_save)
    timestamp = datetime.now().strftime("%d-%m-%Y-%H:%M:%S")  # noqa: DTZ005
    file_path = f"consul_{flow_name}_{timestamp}.md"
    _save_to_markdown(file_path, final_text)
    return file_path
