import re
import textwrap
from typing import TYPE_CHECKING, Any

from prompt_toolkit import prompt
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text

from consul.cli.utils.commands import Commands

if TYPE_CHECKING:
    import loguru

MAX_WIDTH = 120
MIN_WIDTH = 66


def get_ascii_art_logo(console_width: int) -> Text:
    """Generate ASCII art logo scaled to console width."""
    char_scale = max(0, int((console_width - MIN_WIDTH) / 2))

    logo_lines = [
        "",
        f"{'░' * char_scale}░   █████████   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   ████   {'░' * char_scale}",
        f"{' ' * char_scale}   ███░░░░░███                                            ░░███",
        f"{' ' * char_scale}  ███     ░░░    ██████   ████████     █████   █████ ████  ░███",
        f"{' ' * char_scale} ░███           ███░░███ ░░███░░███   ███░░   ░░███ ░███   ░███",
        f"{' ' * char_scale} ░███          ░███ ░███  ░███ ░███  ░░█████   ░███ ░███   ░███",
        f"{' ' * char_scale} ░░███     ███ ░███ ░███  ░███ ░███   ░░░░███  ░███ ░███   ░███",
        f"{' ' * char_scale}  ░░█████████  ░░██████   ████ █████  ██████   ░░████████  █████",
        f"{'░' * char_scale}   ░░░░░░░░░    ░░░░░░   ░░░░ ░░░░░  ░░░░░░     ░░░░░░░░  ░░░░░   {'░' * char_scale}",
        "",
    ]

    logo_text = Text()
    for line in logo_lines:
        logo_text.append(line + "\n", style="cyan")

    return logo_text


class TerminalHandler:
    """Singleton class for all terminal I/O operations in Consul. Use only classmethods; do not instantiate."""

    _console: Console | None = None
    _live_spinner: Live | None = None
    _spinner: Spinner | None = None
    _main_col: str = "cyan"
    _use_colors: bool = True

    def __new__(cls) -> None:
        """Prevent instantiation of TerminalHandler."""
        msg = "TerminalHandler is a static utility class and cannot be instantiated."
        raise RuntimeError(msg)

    @classmethod
    def _init_console(cls) -> Console:
        """Initialize Rich console if not already done."""
        if cls._console is None:
            cls._console = Console(
                width=MAX_WIDTH,
                color_system="auto" if cls._use_colors else None,
                force_terminal=True,
                highlight=False,  # Disable automatic highlighting
            )
        return cls._console

    @classmethod
    def _init_spinner(cls) -> tuple[Live, Spinner]:
        """Initialize spinner components."""
        if cls._live_spinner is None or cls._spinner is None:
            spinner_text = Text("Consuliting artificial neurons...", style=cls._main_col)
            cls._spinner = Spinner("arrow", text=spinner_text, style=cls._main_col)
            cls._live_spinner = Live(
                cls._spinner,
                console=cls._init_console(),
                refresh_per_second=10,
                transient=True,  # Make spinner transient so it disappears when stopped
            )
        return cls._live_spinner, cls._spinner

    @classmethod
    def start_spinner(cls) -> None:
        """Start Rich spinner in the terminal."""
        live_spinner, _ = cls._init_spinner()
        if not live_spinner.is_started:
            live_spinner.start()

    @classmethod
    def stop_spinner(cls) -> None:
        """Stop Rich spinner in the terminal."""
        if cls._live_spinner and cls._live_spinner.is_started:
            cls._live_spinner.stop()
            cls._live_spinner = None
            cls._spinner = None

    @classmethod
    def display_loguru_message(cls, message: "loguru.Message") -> None:
        """
        Logging handler which echoes loguru logger messages into Rich console while keeping its formatting
        and safely handling the spinner instance.
        """

        def emit_message(record: dict[str, Any], formatted_text: Text) -> None:
            """Echo log message with log level taken into account."""
            console = cls._init_console()
            if record["level"].name in ["ERROR", "CRITICAL"]:
                console.print(formatted_text, stderr=True)
            else:
                console.print(formatted_text)

        def format_message(record: dict[str, Any]) -> Text:
            """Format log message according to its level."""
            log_level_color_map = {
                "DEBUG": "blue",
                "INFO": "white",
                "SUCCESS": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            }

            level = record["level"].name
            message_text = record["message"]

            if not cls._use_colors:
                return Text(f"→ [{level}] {record['time'].strftime('%H:%M:%S ')} {message_text}")

            color = log_level_color_map.get(level, "white")

            formatted = Text()
            formatted.append("→ ", style="white")
            formatted.append(f"[{level}] ", style=color)
            formatted.append(record["time"].strftime("%H:%M:%S "), style="white")
            formatted.append(message_text, style=color)

            return formatted

        # Format message according to the logger level
        record = message.record
        formatted_text = format_message(record)

        # Echo message while hiding spinner
        if cls._live_spinner and cls._live_spinner.is_started:
            cls._live_spinner.stop()
            emit_message(record, formatted_text)
            cls._live_spinner.start()
        else:
            emit_message(record, formatted_text)

    @classmethod
    def prompt_user_input(cls) -> str:
        """Get user input with persistent prompt and proper wrapping."""
        console = cls._init_console()
        try:
            console.print("\n", end="")
            console.print(Text("User:", style="blue"))
            user_input = prompt(
                "→ ",  # Simple string prompt
                mouse_support=True,
                wrap_lines=True,
            )
        except KeyboardInterrupt:
            raise
        except EOFError as e:
            raise KeyboardInterrupt from e

        return user_input

    @classmethod
    def display_message(cls, message: str, *, format_markdown: bool = False) -> None:
        """Echo formatted message into terminal."""

        def extract_and_color_prefix(text: str) -> tuple[Text | None, str]:
            """Extract prefix and return colored prefix + remaining text."""
            prefixes_colors = {"User:": "blue", "Assistant:": "green", "Command:": "red"}

            for prefix, color in prefixes_colors.items():
                if text.startswith(prefix):
                    colored_prefix = Text(prefix, style=color) + Text("\n→ ", style="white")
                    remaining_text = text[len(prefix) :]
                    return colored_prefix, remaining_text

            return None, text

        console = cls._init_console()

        # Always apply text wrap first
        message = cls.apply_smart_text_wrap(message)

        # Extract and color prefix, get remaining content
        colored_prefix, content = extract_and_color_prefix(message)

        # Stop spinner temporarily if running
        spinner_was_running = cls._live_spinner and cls._live_spinner.is_started
        if spinner_was_running:
            cls.stop_spinner()

        try:
            console.print("\n", end="")
            # Print colored prefix if it exists
            if colored_prefix:
                console.print(colored_prefix, end="")
            # Print content (either as markdown or plain text)
            if format_markdown:
                md = Markdown(content, code_theme="lightbulb")
                console.print(md)
            else:
                console.print(content)

        finally:
            if spinner_was_running:
                cls.start_spinner()

    @staticmethod
    def apply_smart_text_wrap(message: str) -> str:
        """Wraps text according to max_width while preserving list formatting and indentation."""
        lines = message.split("\n")
        wrapped_lines = []

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
    def echo_intro(cls, flows: list[str]) -> None:
        """Display introductory text to CLI interface of Consul."""
        console = cls._init_console()
        console_width = console.size.width

        # Generate and display logo
        console.print(get_ascii_art_logo(console_width), end="")
        # Prepare intro message
        intro_message = f"Welcome to the Consul CLI! Consul contains set of simple LLM flows and agents for solving small daily problems. Flow can be selected by starting consul with the '--flow' '-f' flag, available flows are: {', '.join(flows)}. During runtime, following commands can be used. {Commands.get_instructions()}."  # noqa: E501
        console.print(cls.apply_smart_text_wrap(intro_message), style=cls._main_col)
        console.print("-" * console_width, style=cls._main_col)

    @classmethod
    def echo_goodbye(cls) -> None:
        """Display goodbye message."""
        console = cls._init_console()
        console_width = console.size.width

        console.print("\n\nSigning off! Bye ツ!", style=cls._main_col)
        console.print(
            "Consul code available at https://github.com/ofinke/consul under MIT licence.", style=cls._main_col
        )
        console.print("-" * console_width, style=cls._main_col)
