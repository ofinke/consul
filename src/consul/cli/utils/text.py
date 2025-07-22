import re
import textwrap
from typing import TYPE_CHECKING, Any

import click
from yaspin import yaspin
from yaspin.spinners import Spinners

from consul.cli.utils.commands import Commands

if TYPE_CHECKING:
    import loguru

MAX_WIDTH = 120
MIN_WIDTH = 66
char_scale = int((MAX_WIDTH - MIN_WIDTH) / 2)

ASCII_ART_LOGO = f"""

{char_scale * "░"}░   █████████   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   ████   {char_scale * "░"}
{char_scale * " "}   ███░░░░░███                                            ░░███
{char_scale * " "}  ███     ░░░    ██████   ████████     █████   █████ ████  ░███
{char_scale * " "} ░███           ███░░███ ░░███░░███   ███░░   ░░███ ░███   ░███
{char_scale * " "} ░███          ░███ ░███  ░███ ░███  ░░█████   ░███ ░███   ░███
{char_scale * " "} ░░███     ███ ░███ ░███  ░███ ░███   ░░░░███  ░███ ░███   ░███
{char_scale * " "}  ░░█████████  ░░██████   ████ █████  ██████   ░░████████  █████
{char_scale * "░"}   ░░░░░░░░░    ░░░░░░   ░░░░ ░░░░░  ░░░░░░     ░░░░░░░░  ░░░░░   {char_scale * "░"}

"""


class TerminalHandler:
    """Singleton class for all terminal I/O operations in Consul. Use only classmethods; do not instantiate."""

    _max_width: int = MAX_WIDTH  # Don't change this bellow the MIN_WIDTH
    _main_col: str = "cyan"
    _spinner: yaspin = None
    _use_colors: bool = True

    def __new__(cls) -> None:
        """Prevent instantiation of TerminalHandler."""
        msg = "TerminalHandler is a static utility class and cannot be instantiated."
        raise RuntimeError(msg)

    @classmethod
    def _init_spinner(cls) -> yaspin:
        """
        Private method to initiate spinner instance. If no special shenanigans with spinner are planned, this doesn't
        need to be called.
        """
        if cls._spinner is None:
            cls._spinner = yaspin(
                Spinners.arrow,
                text=click.style("Consuliting artificial neurons...", fg=cls._main_col),
                color=cls._main_col,
            )
        return cls._spinner

    @classmethod
    def start_spinner(cls) -> None:
        """Start yaspin spinner in the terminal."""
        spinner = cls._init_spinner()
        if not getattr(spinner, "_spin_thread", None):
            spinner.start()

    @classmethod
    def stop_spinner(cls) -> None:
        """Stop yaspin spinnner in the terminal."""
        spinner = cls._init_spinner()
        if getattr(spinner, "_spin_thread", None):
            spinner.stop()
            cls._spinner = None

    # Logger handler
    @classmethod
    def echo_loguru_message(cls, message: "loguru.Message") -> None:
        """
        Logging handler which echoes loguru logger messages into click.echo while keeping its formatting and safely
        handling the spinner instance.
        """

        def emit_message(record: dict[str, Any], formatted: str) -> None:
            """Echo log message with log level taken into account."""
            formatted = cls.apply_smart_text_wrap(formatted)
            if record["level"].name in ["ERROR", "CRITICAL"]:
                click.echo(formatted, err=True, color=cls._use_colors)
            else:
                click.echo(formatted, color=cls._use_colors)

        def format_message(record: dict[str, Any]) -> str:
            """Format log message according to it's level."""
            log_level_color_map = {
                "DEBUG": "blue",
                "INFO": "white",
                "SUCCESS": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            }
            level = record["level"].name
            message = record["message"]
            if not cls._use_colors:
                return f"[{level}] {message}"
            color = log_level_color_map.get(level, "white")
            return (
                "→ "
                + click.style(f"[{level}] ", fg=color)
                + record["time"].strftime("%H:%M:%S %Z")
                + click.style(f" {message}", fg=color)
            )

        # format message according to the logger level
        record = message.record
        formatted = format_message(record)

        # echo message while hiding spinner.
        spinner = cls._init_spinner()
        if getattr(spinner, "_spin_thread", None):
            with spinner.hidden():
                emit_message(record, formatted)
        else:
            emit_message(record, formatted)

    # Echo message into the terminal
    @classmethod
    def echo_message(cls, message: str, *, format_markdown: bool = False) -> None:
        """Echo formatted message into terminal."""
        # apply text wrap
        message = cls.apply_smart_text_wrap(message)
        # apply markdown format
        if format_markdown:
            message = cls.apply_markdown_styling(message)
        # apply color to text prefix ("User:", "AI:", "Command:")
        prefixes_colors = {"User:": "blue", "AI:": "green", "Command:": "red"}
        for prefix, color in prefixes_colors.items():
            if message.startswith(prefix):
                styled_prefix = click.style(prefix[:-1], fg=color)
                message = f"{styled_prefix}:{message[len(prefix) :]}"
                break
        # echo
        click.echo("\n" + message)

    @classmethod
    def apply_smart_text_wrap(cls, message: str) -> str:
        """Wraps text according to max_width while preserving list formatting and indentation."""
        lines = message.split("\n")
        wrapped_lines = []
        # go through each line
        for line in lines:
            if len(line) <= MAX_WIDTH:
                wrapped_lines.append(line)
            else:
                # Detect list items and their indentation
                list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+", line)
                if list_match:
                    indent = list_match.group(1)
                    marker = list_match.group(2)
                    hanging_indent = len(indent) + len(marker) + 1
                    wrapped = textwrap.fill(
                        line, width=MAX_WIDTH, initial_indent="", subsequent_indent=" " * hanging_indent
                    )
                else:
                    leading_space_match = re.match(r"^(\s*)", line)
                    leading_space = leading_space_match.group(1) if leading_space_match else ""
                    wrapped = textwrap.fill(line, width=MAX_WIDTH, initial_indent="", subsequent_indent=leading_space)

                wrapped_lines.append(wrapped)
        return "\n".join(wrapped_lines)

    @classmethod
    def apply_markdown_styling(cls, message: str) -> str:
        """
        Converts predefined styles to markdown for a pretty print in terminal.
        Applies styling to the entire message (multi-line supported). Supports:
            - Inline code: `code`
            - Code blocks: ```code block```
            - Bold: **bold** or __bold__.
        """

        def style_codeblock(match: re.Match) -> str:
            code_content = match.group(2)
            return click.style(code_content, fg=(0, 0, 0))

        def style_inline_code(match: re.Match) -> str:
            code_content = match.group(1)
            return click.style(code_content, fg=(0, 0, 0))

        def style_bold(match: re.Match) -> str:
            bold_content = match.group(1)
            return click.style(bold_content, fg="cyan", bold=True)

        # Only matches fenced code blocks surrounded by newlines
        codeblock_pattern = re.compile(r"(^|\n)```(?:\w+)?\n([\s\S]*?)\n```(\n|$)", re.MULTILINE)

        # iterate over codeblock patterns
        segments = []
        last_end = 0
        for match in codeblock_pattern.finditer(message):
            # Non-code before this code block
            non_code = message[last_end : match.start()]
            if non_code:
                non_code = re.sub(r"`([^`]+)`", style_inline_code, non_code)
                non_code = re.sub(r"\*\*([^*]+)\*\*", style_bold, non_code)
                non_code = re.sub(r"__([^_]+)__", style_bold, non_code)
                segments.append(non_code)
            code = style_codeblock(match)
            segments.append(code)
            last_end = match.end()
        remainder = message[last_end:]
        if remainder:
            remainder = re.sub(r"`([^`]+)`", style_inline_code, remainder)
            remainder = re.sub(r"\*\*([^*]+)\*\*", style_bold, remainder)
            remainder = re.sub(r"__([^_]+)__", style_bold, remainder)
            segments.append(remainder)

        return "\n".join(segments)

    # App intro and outro messages
    @classmethod
    def echo_intro(cls, flows: list[str]) -> None:
        """Display introductory text to CLI interface of Consul."""
        # prepare intro message
        intro_message = f"Welcome to the Consul CLI! Consul contains set of simple LLM flows and agents for solving small daily problems. Flow can be selected by starting consul with the '--flow' '-f' flag, available flows are: {', '.join(flows)}. During runtime, following commands can be used. {Commands.get_instructions()}."  # noqa: E501

        click.echo(click.style(ASCII_ART_LOGO, fg=cls._main_col))
        click.echo(click.style(textwrap.fill(intro_message, width=cls._max_width), fg=cls._main_col))
        click.echo(click.style("-" * cls._max_width, fg=cls._main_col))

    @classmethod
    def echo_goodbye(cls) -> None:
        """Display goodbye message."""
        click.echo(click.style("\n\nSigning off! Bye ツ!", fg=cls._main_col))
        click.echo(
            click.style(
                "Consul code available at https://github.com/ofinke/consul under MIT licence.", fg=cls._main_col
            )
        )
        click.echo(click.style("-" * cls._max_width, fg=cls._main_col))
