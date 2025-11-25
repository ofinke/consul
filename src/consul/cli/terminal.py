import functools
import re
import textwrap
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from prompt_toolkit import prompt
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.table import Table, box
from rich.text import Text
from rich.traceback import Traceback

if TYPE_CHECKING:
    import loguru


class TerminalHandler:
    """
    Class for all terminal I/O operations in Consul.
    Expected usage is having a single instance of this class across the whole app.
    """

    csl: Console
    # spinner
    live_spinner: Live | None = None
    spinner: Spinner | None = None
    # config
    cfg_main_color: str = "cyan"  # cyan / yellow
    cfg_use_colors: bool = True
    cfg_max_width: int = 120
    cfg_min_width: int = 66
    cfg_spinner_msg: str = "Consulting artificial neurons..."
    cfg_spinner_style: str = "arrow"
    cfg_code_theme: str = "lightbulb"
    cfg_log_cmap: ClassVar[dict[str, str]] = {
        "DEBUG": "blue",
        "INFO": "white",
        "SUCCESS": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red",
    }
    cfg_cmd_cmap: ClassVar[dict[str, str]] = {
        "assistant:": "green",
        "user:": "blue",
        "command:": cfg_main_color,
    }

    def __init__(self) -> None:
        """Start the terminal instance by initializing the Console object."""
        self.csl = Console(
            width=self.cfg_max_width,
            color_system="auto" if self.cfg_use_colors else None,
            force_terminal=True,
            highlight=False,  # Disable automatic highlighting
        )

    # Spinner managment

    def _init_spinner(self, message: str | None = None) -> tuple[Live, Spinner]:
        """Initialize spinner components."""
        if self.live_spinner is None or self.spinner is None:
            spinner_text = (
                Text(message, style=self.cfg_main_color)
                if message
                else Text(self.cfg_spinner_msg, style=self.cfg_main_color)
            )
            self.spinner = Spinner(self.cfg_spinner_style, text=spinner_text, style=self.cfg_main_color)
            self.live_spinner = Live(
                self.spinner,
                console=self.csl,
                refresh_per_second=60,
                transient=True,  # Make spinner transient so it disappears when stopped
            )
        return self.live_spinner, self.spinner

    def start_spinner(self, message: str | None = None) -> None:
        """Start Rich spinner in the terminal."""
        live_spinner, _ = self._init_spinner(message=message)
        if not live_spinner.is_started:
            live_spinner.start()

    def stop_spinner(self) -> None:
        """Stop Rich spinner in the terminal."""
        if self.live_spinner and self.live_spinner.is_started:
            self.live_spinner.stop()
            self.live_spinner = None
            self.spinner = None

    def restart_spinner(self, message: str | None = None) -> None:
        """Restarts Rich spinner with a specific message."""
        self.stop_spinner()
        self.start_spinner(message)

    # Displaying messages

    def _apply_smart_text_wrap(self, message: str) -> str:
        """Wraps text according to max_width while preserving list formatting and indentation."""
        lines = message.split("\n")
        wrapped_lines = []

        for line in lines:
            if len(line) <= self.cfg_max_width:
                wrapped_lines.append(line)
            else:
                # Detect list items and their indentation
                list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+", line)
                if list_match:
                    indent = list_match.group(1)
                    marker = list_match.group(2)
                    hanging_indent = len(indent) + len(marker) + 1
                    wrapped = textwrap.fill(
                        line, width=self.cfg_max_width, initial_indent="", subsequent_indent=" " * hanging_indent
                    )
                else:
                    leading_space_match = re.match(r"^(\s*)", line)
                    leading_space = leading_space_match.group(1) if leading_space_match else ""
                    wrapped = textwrap.fill(
                        line, width=self.cfg_max_width, initial_indent="", subsequent_indent=leading_space
                    )
                wrapped_lines.append(wrapped)

        return "\n".join(wrapped_lines)

    def _get_logo(self) -> str:
        """Generate ASCII art logo scaled to console width."""
        char_scale = max(0, int((self.cfg_max_width - self.cfg_min_width) / 2))

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
            logo_text.append(line + "\n", style=self.cfg_main_color)

        return logo_text

    def display_loguru_message(self, message: "loguru.Message") -> None:
        """
        Logging handler which echoes loguru logger messages into Rich console while keeping its formatting
        and safely handling the spinner instance.
        """

        def emit_message(record: dict, formatted_text: Text) -> None:
            """Echo log message (and exception, if any) with log level taken into account."""
            # Print the main log message
            self.csl.print(formatted_text)
            # Print traceback if present
            if record.get("exception"):
                exc = record["exception"]
                tb_renderable = Traceback.from_exception(
                    exc.type,
                    exc.value,
                    exc.traceback,
                    width=self.csl.size.width,
                    show_locals=False,
                    max_frames=10 if self.cfg_use_colors else None,
                )
                self.csl.print(tb_renderable)

        def format_message(record: dict[str, Any]) -> Text:
            """Format log message according to its level."""
            level = record["level"].name
            message_text = record["message"]

            if not self.cfg_use_colors:
                return Text(f"→ [{level}] {record['time'].strftime('%H:%M:%S ')} {message_text}")

            color = self.cfg_log_cmap.get(level, "white")

            formatted = Text()
            formatted.append(f"[{level}] ", style=color)
            formatted.append(record["time"].strftime("%H:%M:%S "), style="white")
            formatted.append(message_text, style=color)

            return formatted

        # Format message according to the logger level
        record = message.record
        formatted_text = format_message(record)

        # Echo message while hiding spinner
        if self.live_spinner and self.live_spinner.is_started:
            self.live_spinner.stop()
            emit_message(record, formatted_text)
            self.live_spinner.start()
        else:
            emit_message(record, formatted_text)

    def display_message(self, message: str) -> None:
        """
        Echo formatted message into terminal.
        Use predefined printing format for messages by starting the message with one of the prefixes: 'user:' or
        'assistant:' for messages meant for conversation with AI, or 'command:' prefix to print system answers to user
        commands. When no prefix is used, the message is printed as it is.
        """

        def display_conversation_message(text: str, prefix: str) -> None:
            """Unified function to print messages with 'user:' or 'assistant:' prefixes."""
            # Define the full message we want to print from a newline and wrap it
            wtext = self._apply_smart_text_wrap(f"→ {text[len(prefix) :].lstrip()}")
            self.csl.print("\n", end="")
            self.csl.print(Text(prefix.capitalize(), style=self.cfg_cmd_cmap.get(prefix, "white")))
            self.csl.print(Markdown(wtext, code_theme=self.cfg_code_theme))

        def display_command_message(txt: str, prefix: str) -> None:
            """Unified function to print messages with 'command:' prefix."""
            self.csl.print("\n", end="")
            cl = self.cfg_cmd_cmap.get(prefix, "white")
            # Construct the raw message and wrap it:
            dt = datetime.now(UTC).strftime(" %H:%M:%S ")
            prefix = f"[{prefix[:-1].capitalize()}]"
            msg = f"{prefix} {dt} {txt[len(prefix) :].lstrip()}"
            wmsg = self._apply_smart_text_wrap(msg)
            # Now, we recreate the message with styles with correct wrap.
            wsmsg = (
                Text(prefix, style=cl)
                + Text(dt, style="white")
                + Text(wmsg[len(prefix) + len(dt) + 2 :].lstrip(), style=cl)
            )
            self.csl.print(wsmsg)

        # Stop spinner temporarily if running
        spinner_was_running = self.live_spinner and self.live_spinner.is_started
        if spinner_was_running:
            self.stop_spinner()

        # Print the message according to prefix.
        prefix = next((p for p in self.cfg_cmd_cmap if message.lower().startswith(p)), None)
        try:
            if prefix in ["user:", "assistant:"]:
                display_conversation_message(message, prefix)
            elif prefix == "command:":
                display_command_message(message, prefix)
            else:
                self.csl.print("\n", end="")
                self.csl.print(Markdown(self._apply_smart_text_wrap(message), code_theme=self.cfg_code_theme))
        finally:
            if spinner_was_running:
                self.start_spinner()

    def display_table(
        self, cols: tuple[str], rows: list[tuple[str]], cap: str | None = None, tit: str | None = None
    ) -> None:
        """Prints data in unified table design, all data prep needs to be done before calling."""
        # Define table and its styles
        table = Table(
            title=tit,
            caption=cap,
            box=box.MINIMAL_HEAVY_HEAD,
            leading=1,
            header_style=self.cfg_main_color,
            caption_style=self.cfg_main_color,
            width=self.csl.width
        )
        # Define columns and rows
        for col in cols:
            table.add_column(col)
        for row in rows:
            table.add_row(*row)
        # print
        self.csl.print(table)

    def echo_intro(self, flows: list[str]) -> None:
        """Display introductory text to CLI interface of Consul."""
        # Generate and display logo
        self.csl.print(self._get_logo(), end="")
        # Prepare intro message
        intro_message = f"Welcome to the Consul CLI! Consul contains set of simple LLM flows and agents for solving small daily problems. Flow can be selected by starting consul with the '--flow' '-f' flag, available flows are: {', '.join(flows)}.\nWrite '/h' or '/help' to print supported commands."  # noqa: E501
        self.csl.print(self._apply_smart_text_wrap(intro_message), style=self.cfg_main_color)
        self.csl.print("-" * self.cfg_max_width, style=self.cfg_main_color)

    def echo_goodbye(self) -> None:
        """Display goodbye message."""
        self.csl.print("\nSigning off! Bye ツ!", style=self.cfg_main_color)
        self.csl.print("Available at https://github.com/ofinke/consul under MIT licence.", style=self.cfg_main_color)
        self.csl.print("-" * self.cfg_max_width, style=self.cfg_main_color)

    # User input

    def prompt_user_input(self, show_prompt: str = "→ ") -> str:
        """Get user input with persistent prompt and proper wrapping."""
        spinner_was_running = self.live_spinner and self.live_spinner.is_started
        if spinner_was_running:
            self.stop_spinner()
        try:
            self.csl.print("\n", end="")
            self.csl.print(Text("User:", style="blue"))
            user_input = prompt(
                show_prompt,
                # mouse_support=True,
                wrap_lines=True,
                enable_history_search=True,
                search_ignore_case=True,
            )
        except KeyboardInterrupt:
            raise
        except EOFError as e:
            raise KeyboardInterrupt from e
        else:
            return user_input
        finally:
            if spinner_was_running:
                self.start_spinner()


@functools.cache
def get_terminal_handler() -> TerminalHandler:
    """Returns the TerminalHandler instance."""
    return TerminalHandler()
