import click
from loguru import logger
from loguru._handler import Message

COLOR_MAP = {
    "DEBUG": "blue",
    "INFO": "white",
    "SUCCESS": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red",
}


class LoguruHandler:
    def __init__(self, level: str = "INFO", *, use_colors: bool = True) -> None:
        """Custom loguru handler that uses click.echo for output."""
        self.level = level
        self.use_colors = use_colors

    def write(self, message: Message) -> None:
        """Handler function for loguru."""
        record = message.record

        # Format the message
        formatted = self._format_message(record)

        # Choose output stream and color based on level
        if record["level"].name in ["ERROR", "CRITICAL"]:
            click.echo(formatted, err=True, color=self.use_colors)
        else:
            click.echo(formatted, color=self.use_colors)

    def _format_message(self, record: dict) -> str:
        """Format log message for click output."""
        level = record["level"].name
        message = record["message"]

        if not self.use_colors:
            return f"[{level}] {message}"

        color = COLOR_MAP.get(level, "white")
        return click.style(f"[{level}] {message}", fg=color)


# Usage example
def setup_loguru_intercept(*, verbose: bool = False, quiet: bool = False) -> None:
    """Setup logging configuration."""
    # Remove default handler
    logger.remove()

    # Determine log level
    if quiet:
        level = "WARNING"
    elif verbose:
        level = "DEBUG"
    else:
        level = "INFO"

    # Add click handler for CLI output
    click_handler = LoguruHandler(level=level)
    logger.add(click_handler.write, level=level, format="{message}")
