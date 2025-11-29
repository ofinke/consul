import string
from collections.abc import Callable
from typing import ClassVar

from langchain.messages import AIMessage, HumanMessage, ToolMessage
from loguru import logger
from sqlalchemy import func, select

from consul.cli.exceptions import CommandInterrupt
from consul.cli.terminal import get_terminal_handler
from consul.cli.utils.save import save_memory
from consul.core.config import AvailableFlow
from consul.db.handler import get_db_handler
from consul.db.tables import MessageLogTable
from consul.flows.logging import LoggingHandler
from consul.flows.session import FlowSession


class CommandProcessor:
    """
    Class which defines all available user commands and handles their execution.
    Each command has a corresponding method starting with prefix 'cmd_', supporting methods start with '_'. Commands
    can be registered using the `register_command` method and default commands with their description are defined in the
    'register_default_commands' method. To correctly execute a command, the 'process_input' should be invoked.
    """

    # Alphabet used for the base36 encoding / decoding
    ALPHABET36: ClassVar[str] = string.digits + string.ascii_lowercase

    def __init__(self, session: FlowSession) -> None:
        """Init class for user commands execution."""
        self.session = session
        self.io = get_terminal_handler()
        self.db = get_db_handler()
        self.commands = {}
        self.register_default_commands()

        # state and config variables used mainly to handle and update stare related to commands for db managment
        self.st_load: int = 10
        self.st_view: int = 10
        self.st_latest_table: str = "h"
        self.st_history_cols = ("ID", "First user message", "Flow", "Archive")

    def register_command(self, name: str, handler: Callable, aliases: list[str] | None = None, desc: str = "") -> None:
        """Register command into instance registry."""
        for cmd in [name] + (aliases or []):
            self.commands[cmd] = {"handler": handler, "help": desc}

    def register_default_commands(self) -> None:
        """Definition of default commands."""
        # General commands
        self.register_command(
            "h",
            self.cmd_help,
            aliases=["help"],
            desc="Show list of commands",
        )
        self.register_command("q", self.cmd_exit, aliases=["quit"], desc="Exit the application")
        self.register_command(
            "p",
            self.cmd_print,
            desc="Print current conversation history to markdown, or specific using ID.",
        )
        # History manipulation
        self.register_command("r", self.cmd_clear, desc="Clear session history")
        self.register_command("f", self.cmd_flow, desc="Change used flow")
        self.register_command("a", self.cmd_archive, desc="Archive current conversation with optional metadata")
        self.register_command("l", self.cmd_db_load, desc="Load conversation using ID")
        self.register_command("b", self.cmd_back, desc="Remove last N turns")
        self.register_command("v", self.cmd_db_view, desc="View 10 latest conversations from history db.")
        # self.register_command("e", self.cmd_db_exit, desc="Exit DB view")
        self.register_command("u", self.cmd_db_up, desc="Scroll up in DB view")
        self.register_command("d", self.cmd_db_down, desc="Scroll down in DB view")

    def process_input(self, input_str: str) -> None:
        # Split chained commands: /l 345 /b 2
        parts = input_str.strip().split("/")
        for part in parts:
            if not part:
                continue
            tokens = part.strip().split()
            cmd = tokens[0]
            args = tokens[1:]
            if cmd in self.commands:
                self.commands[cmd]["handler"](args)
            else:
                self.io.display_message(f"Command: Unknown command '{cmd}'")

    # COMMANDS

    def cmd_help(self, _: list[str]) -> None:
        """Prints all available commands and their definition."""
        # TODO: make this pretty and organized, under tags
        cmds = "\n".join(f"/{cmd} - {meta['help']}" for cmd, meta in self.commands.items())
        self.io.display_message(cmds)

    def cmd_exit(self, _: list[str]) -> None:
        """Stops app."""
        raise CommandInterrupt

    def cmd_clear(self, _: list[str]) -> None:
        """Clears current session history."""
        self.session.clear_history()
        self.io.display_message("Command: Session chat history cleared!")

    def cmd_flow(self, args: list[str]) -> None:
        """Changes session flow while keeping history."""
        name = "".join(args)
        try:
            run_this_flow = AvailableFlow(name)
        except ValueError:
            logger.warning(f"'{name}' not a name of existing flow, starting 'chat' flow")
            run_this_flow = AvailableFlow("chat")
        finally:
            self.session.change_flow(run_this_flow)
            self.io.display_message(f"Command: Starting {self.session.str_flow_info}")

    def cmd_print(self, _: list[str]) -> None:
        """Save current history into a markdown file."""
        path_to_saved_file = save_memory(self.session.chat_history, self.session.flow.config.name)
        self.io.display_message(f"Command: Conversation history saved at '{path_to_saved_file}'.")

    def cmd_back(self, args: list[str]) -> None:
        """Removes N turns from conversation (turn = everything from latest human message)."""
        steps = int(args[0]) if args else 1
        # take history from session and go from the back, counting the number of human messages. Cut the history before
        # the steps human message
        history = self.session.chat_history
        count = 0
        for i in range(len(history) - 1, -1, -1):
            if isinstance(history[i], HumanMessage):
                count += 1
                if count == steps:
                    new_history = history[:i]  # cut before this HumanMessage
                    break

        if count < steps:
            logger.warning(f"History has only {count} turns. Cannot go {steps} turns back. History wasn't changed.")
            return

        # Clear history to reset conversation id and then replace it with the new one
        self.session.clear_history()
        self.session.chat_history = new_history

        # print the whole history and also log it into the database as a new conversation
        fake_state = {"cid": self.session.cid, "flow": self.session.flow.flow_name.value, "messages": []}
        log_handler = LoggingHandler()
        for msg in new_history:
            if isinstance(msg, HumanMessage):
                self.io.display_message(f"User: {msg.text}")
            if isinstance(msg, AIMessage):
                self.io.display_message(f"Assistant: {msg.text}")
            fake_state["messages"].append(msg)
            log_handler.log_message(fake_state)

        # Inform user
        self.io.display_message(f"Command: Removed last {steps} turn(s) and created new conversation history.")

    def cmd_db_view(self, args: list[str]) -> None:
        """Show latest 10 rows from the database view."""
        self.st_load = 10

        # handle case when arguments are missing or invalid
        if args and args[0].lower() == "a":
            self.st_latest_table = "a"
        else:
            self.st_latest_table = "h"

        # load and display latest db view data
        data = self._get_history_db_data()
        self.io.display_table(self.st_history_cols, self._parse_db_data(data))
        self.io.display_message(
            f"Command: Showing last {self.st_view} from {self.st_load} latest{' archived ' if self.st_latest_table == 'a' else ' '}conversations."  # noqa: E501
        )

    def cmd_db_down(self, args: list[str]) -> None:
        """Scroll down the database history."""
        self.st_load += int(args[0]) if args else 10
        data = self._get_history_db_data()
        self.io.display_table(self.st_history_cols, self._parse_db_data(data))
        self.io.display_message(f"Command: Showing last {self.st_view} from {self.st_load} latest conversations.")

    def cmd_db_up(self, _: list[str]) -> None:
        """Scroll down the database history."""
        self.st_load = max(self.st_load - 10, 10)
        data = self._get_history_db_data()
        self.io.display_table(self.st_history_cols, self._parse_db_data(data))
        self.io.display_message(f"Command: Showing last {self.st_view} from {self.st_load} latest conversations.")

    def cmd_db_load(self, args: list[str]) -> None:
        """Loads conversation from history from database."""
        if not args:
            self.io.display_message("Command: Please provide a message ID.")
            return

        try:
            message_id = self.decode_base36(args[0])
        except ValueError:
            self.io.display_message("Command: Invalid ID format. Must be an integer.")
            return

        # First, get the cid for the given message ID
        cid_stmt = select(MessageLogTable.cid).where(MessageLogTable.id == message_id)
        cid_result = self.db.load(MessageLogTable, statement=cid_stmt)
        if not cid_result:
            self.io.display_message(f"Command: No conversation found for ID {message_id}.")
            return

        cid = cid_result[0][0]

        # Now retrieve all messages for this cid ordered by oldest first
        conv_stmt = (
            select(
                MessageLogTable.cid,
                MessageLogTable.author,
                MessageLogTable.flow,
                MessageLogTable.content_blocks,
                MessageLogTable.tool_call_id,
            )
            .where(MessageLogTable.cid == cid)
            .order_by(MessageLogTable.created_at.asc())
        )
        conversation_data = self.db.load(MessageLogTable, statement=conv_stmt)

        if not conversation_data:
            self.io.display_message(f"Command: No messages found for conversation {cid}.")
            return

        # Create the new history
        self.session.clear_history()
        self.session.change_flow(AvailableFlow(conversation_data[0][2]))
        self.session.cid = cid
        new_history = []
        for row in conversation_data:
            if row[1] == "human":
                new_history.append(HumanMessage(content_blocks=row[3]))
                self.io.display_message(f"User: {new_history[-1].text}")
            if row[1] == "ai":
                new_history.append(AIMessage(content_blocks=row[3]))
                self.io.display_message(f"Assistant: {new_history[-1].text}") if new_history[-1].text else None
            if row[1] == "tool":
                new_history.append(ToolMessage(content_blocks=row[3], tool_call_id=row[4]))
        self.session.chat_history = new_history

        self.io.display_message(f"Command: Loaded conversation with ID {message_id}")

    def cmd_archive(self, args: list[str]) -> None:
        """Takes current chat history and updates existing db rows witch archive flag and metadata values."""
        metadata = self._parse_metadata(args)

        updated_rows = self.db.update(
            MessageLogTable,
            filters={"cid": self.session.cid},
            update_values={"archived": True, "custom_metadata": metadata},
        )
        self.io.display_message(f"Command: Conversation '{self.session.cid}' archived. ({updated_rows} rows updated)")

    # SUPPORTING METHODS

    @classmethod
    def encode_base36(cls, val: int) -> str:
        """Encode a positive integer into a base36 string."""
        if val < 0:
            msg = "Number must be non-negative"
            raise ValueError(msg)
        if val == 0:
            return cls.ALPHABET36[0]

        result = []
        while val > 0:
            val, remainder = divmod(val, 36)
            result.append(cls.ALPHABET36[remainder])
        return "".join(reversed(result))

    @classmethod
    def decode_base36(cls, val: str) -> int:
        """Decodes base36 number (repsented by string) into base10 integer."""
        val = val.strip().lower()
        if not all(c in cls.ALPHABET36 for c in val):
            msg = "Invalid base36 string"
            raise ValueError(msg)
        num = 0
        for char in val:
            num = num * 36 + cls.ALPHABET36.index(char)
        return num

    def _get_history_db_data(self) -> list[tuple]:
        """Load 'self.load' data from history and convert them into table printable format."""
        # Query the first message for each unique cid (by smallest id),
        # returning id, cid, message, and flow, ordered by newest conversation start,
        # limited to 5.
        subq = select(func.min(MessageLogTable.id).label("min_id")).group_by(MessageLogTable.cid).subquery()
        statement = (
            select(
                MessageLogTable.id,
                MessageLogTable.content_blocks,
                MessageLogTable.flow,
                MessageLogTable.archived,
            )
            .join(subq, MessageLogTable.id == subq.c.min_id)
            .order_by(MessageLogTable.created_at.desc())
            .limit(self.st_load)
        )
        # apply filter for archives if user selected archived table view
        if self.st_latest_table == "a":
            statement = statement.where(MessageLogTable.archived.is_(True))

        data = self.db.load(MessageLogTable, statement=statement)

        # Convert data for better readability. Especially the next() call is really lovely lol. It takes first text from
        # langchains content_blocks and truncate the string according to the desired limit.
        lim = 300
        udata = [
            (
                self.encode_base36(row[0]),
                f"{next((d['text'][:lim] for d in row[1] if d.get('type') == 'text'), '')}{'...' if len(row[2]) > lim else ''}",  # noqa: E501
                row[2],
                "O" if row[3] else "X",
            )
            for row in data
        ]

        return udata[-self.st_view :]

    def _parse_db_data(self, data: list[tuple]) -> list[tuple]:
        """Convert raw data from _get_history_db_data table into human readable format."""
        # TODO: Move the data parsing from _get_history_db_data and make it more readable.
        return data

    def _parse_metadata(self, args: list[str]) -> dict[str, str]:
        """Parses metadata in format key=value into dict {"key" : "value"}."""
        metadata = {}
        for arg in args:
            if "=" in arg:
                k, v = arg.split("=", 1)
                metadata[k] = v
        return metadata
