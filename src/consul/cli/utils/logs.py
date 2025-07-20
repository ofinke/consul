from typing import Any

import click
from loguru import logger
from loguru._handler import Message
from yaspin import yaspin

COLOR_MAP = {
    "DEBUG": "blue",
    "INFO": "white",
    "SUCCESS": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red",
}


class LoguruHandler:
    def __init__(self, *, spinner: yaspin, verbose: bool = False, quiet: bool = False, use_colors: bool = True) -> None:
        # Remove default handler
        logger.remove()

        # Determine log level
        if quiet:
            level = "WARNING"
        elif verbose:
            level = "DEBUG"
        else:
            level = "INFO"

        """Custom loguru handler that uses click.echo for output."""
        self._use_colors = use_colors
        self._spinner = spinner

        logger.add(self.write, level=level, format="{message}")

    def _is_spinner_running(self) -> bool:
        return getattr(self._spinner, "_spin_thread", None) is not None

    def write(self, message: Message) -> None:
        """Handler function for loguru."""
        record = message.record

        # Format the message
        formatted = self._format_message(record)

        # Choose output stream and color based on level
        if self._is_spinner_running():
            with self._spinner.hidden():
                self._emit(record, formatted)
        else:
            self._emit(record, formatted)

    def _emit(self, record: dict[str, Any], formatted: str) -> None:
        """Emit message into click.echo."""
        if record["level"].name in ["ERROR", "CRITICAL"]:
            click.echo(formatted, err=True, color=self._use_colors)
        else:
            click.echo(formatted, color=self._use_colors)

    def _format_message(self, record: dict) -> str:
        """Format log message for click output."""
        level = record["level"].name
        message = record["message"]

        if not self._use_colors:
            return f"[{level}] {message}"

        color = COLOR_MAP.get(level, "white")
        return click.style(f"> [{level}] {message}", fg=color)
