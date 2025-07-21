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


def smart_text_wrap(text: str) -> str:
    """Wrap text line by line, only wrapping lines that exceed the width. Preserves list formatting and indentation."""
    lines = text.split("\n")
    wrapped_lines = []
    in_codeblock = False

    for line in lines:
        # Check for codeblock markers
        if line.strip().startswith("```"):
            in_codeblock = not in_codeblock
            # Skip the codeblock marker lines entirely
            continue

        # Apply markdown styling and remove markdown codes
        styled_line, clean_line = apply_markdown_styling(line, in_codeblock)

        if len(clean_line) <= MAX_WIDTH:
            wrapped_lines.append(styled_line)
        else:
            # For long lines, we need to wrap the clean text first, then style
            # Detect list items and their indentation on the clean text
            list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+", clean_line)
            if list_match:
                # Handle list items
                indent = list_match.group(1)  # Leading whitespace
                marker = list_match.group(2)  # List marker (-, *, +, or number.)
                # Calculate the hanging indent (indent + marker + space)
                hanging_indent = len(indent) + len(marker) + 1
                wrapped = textwrap.fill(
                    clean_line, width=MAX_WIDTH, initial_indent="", subsequent_indent=" " * hanging_indent
                )
            else:
                # Handle regular lines - preserve any leading whitespace
                leading_space_match = re.match(r"^(\s*)", clean_line)
                leading_space = leading_space_match.group(1) if leading_space_match else ""
                wrapped = textwrap.fill(clean_line, width=MAX_WIDTH, initial_indent="", subsequent_indent=leading_space)

            # Apply styling to the wrapped text
            styled_wrapped, _ = apply_markdown_styling(wrapped, in_codeblock)
            wrapped_lines.append(styled_wrapped)

    return "\n".join(wrapped_lines)


def apply_markdown_styling(text: str, in_codeblock: bool = False) -> tuple[str, str]:
    """Apply markdown styling to text and return (styled_text, clean_text)."""
    clean_text = text

    if in_codeblock:
        # Inside a codeblock - green text, no background
        return click.style(text, fg=(0, 0, 0)), clean_text

    # Handle inline code blocks first (single backticks)
    def style_inline_code(match):
        code_content = match.group(1)  # Content between backticks
        return click.style(code_content, fg=(0, 0, 0))

    def clean_inline_code(match):
        return match.group(1)  # Just return the content, remove backticks

    # Handle bold text (**text** or __text__)
    def style_bold(match):
        bold_content = match.group(1)  # Content between markers
        return click.style(bold_content, fg="cyan", bold=True)

    def clean_bold(match):
        return match.group(1)  # Just return the content, remove markers

    # Create clean text (remove markdown codes)
    clean_text = re.sub(r"`([^`]+)`", clean_inline_code, clean_text)
    clean_text = re.sub(r"\*\*([^*]+)\*\*", clean_bold, clean_text)
    clean_text = re.sub(r"__([^_]+)__", clean_bold, clean_text)

    # Create styled text (apply colors but remove markdown codes)
    styled_text = re.sub(r"`([^`]+)`", style_inline_code, text)
    styled_text = re.sub(r"\*\*([^*]+)\*\*", style_bold, styled_text)
    styled_text = re.sub(r"__([^_]+)__", style_bold, styled_text)

    return styled_text, clean_text


class TerminalHandler:
    """Unifying class to handle all outputs into terminal."""

    _max_width: int = MAX_WIDTH  # Don't change this bellow the MIN_WIDTH
    _main_col: str = "cyan"
    _spinner: yaspin = None
    _use_colors: bool = True

    def __init__(self):
        pass

    @classmethod
    def spinner(cls) -> yaspin:
        if cls._spinner is None:
            cls._spinner = yaspin(
                Spinners.noise,
                text=click.style("Consuliting artificial neurons...", fg=cls._main_col),
                color=cls._main_col,
            )
        return cls._spinner

    @classmethod
    def start_spinner(cls) -> None:
        spinner = cls.spinner()
        if not getattr(spinner, "_spin_thread", None):
            spinner.start()

    @classmethod
    def stop_spinner(cls) -> None:
        spinner = cls.spinner()
        if getattr(spinner, "_spin_thread", None):
            spinner.stop()

    # Logger handler
    @classmethod
    def echo_loguru_message(cls, message: "loguru.Message") -> None:
        def emit_message(record: dict[str, Any], formatted: str) -> None:
            """Echo log message with log level taken into account."""
            formatted = smart_text_wrap(formatted)
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
            return click.style(f"> [{level}] {message}", fg=color)

        record = message.record
        formatted = format_message(record)

        # print message while hiding spinner.
        spinner = cls.spinner()
        if getattr(spinner, "_spin_thread", None):
            with spinner.hidden():
                emit_message(record, formatted)
        else:
            emit_message(record, formatted)

    # App intro and outro messages
    @classmethod
    def echo_intro(cls, flows: list[str]) -> None:
        """Prints introductory text to CLI interface of Consul."""
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
