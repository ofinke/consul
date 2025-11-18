from collections.abc import Callable

from langchain.messages import AIMessage, HumanMessage, ToolMessage
from loguru import logger
from sqlalchemy import func, select

from consul.cli.exceptions import CommandInterrupt
from consul.cli.utils.save import save_memory
from consul.cli.utils.text import get_terminal_handler
from consul.core.config.flows import AvailableFlow
from consul.db.handler import get_db_handler
from consul.db.tables import MessageLogTable
from consul.flows.logging import LoggingHandler
from consul.flows.session import FlowSession


class DatabaseCommandProcessor:
    """Class holding Command operations related to database."""

    # TODO: Update _get_history_db_data when archive is implemented in the history table.
    # Will probably want to show ID, First message / Summary, Flow, Archive flag, ?metadata?

    # TODO: Implement arg into db_view (a, archive) which prints only latest messages with archive falg True

    def __init__(self, session: FlowSession) -> None:
        self.load: int = 10
        self.view: int = 10
        self.latest_table: str = "h"
        self.session = session
        self.db = get_db_handler()
        self.io = get_terminal_handler()
        self.cfg_history_cols = ("ID", "Conversation ID", "First user message", "Flow")

    def _get_history_db_data(self) -> list[tuple]:
        """Load 'self.load' data from history and convert them into table printable format."""
        # Query the first message for each unique cid (by smallest id),
        # returning id, cid, message, and flow, ordered by newest conversation start,
        # limited to 5.
        subq = select(func.min(MessageLogTable.id).label("min_id")).group_by(MessageLogTable.cid).subquery()
        statement = (
            select(MessageLogTable.id, MessageLogTable.cid, MessageLogTable.message, MessageLogTable.flow)
            .join(subq, MessageLogTable.id == subq.c.min_id)
            .order_by(MessageLogTable.created_at.desc())
            .limit(self.load)
        )
        data = self.db.load(MessageLogTable, statement=statement)

        # Convert data for better readability

        lim = 300
        udata = [
            (str(row[0]), f"...{row[1][-13:]}", f"{row[2][:lim]}{'...' if len(row[2]) > lim else ''}", row[3])
            for row in data
        ]
        return udata[-self.view :]

    def db_view(self, args: list[str]) -> None:
        """Show latest 10 rows from the database view."""
        self.load = 10
        self.latest_table: str = "h"
        caption = "Latest 10 conversations stored in the history database. Showing first user message."
        self.io.display_table(self.cfg_history_cols, self._get_history_db_data(), cap=caption)

    # def cmd_arch_view(self, _: list[str]) -> None:
    #     """Show latest messages from archive."""

    def db_down(self, args: list[str]) -> None:
        """Scroll down the database history."""
        self.load += int(args[0]) if args else 10
        caption = "TBD."
        self.io.display_table(self.cfg_history_cols, self._get_history_db_data(), cap=caption)

    def db_up(self, _: list[str]) -> None:
        """Scroll down the database history."""
        self.load = max(self.load - 10, 10)
        caption = "TBD."
        self.io.display_table(self.cfg_history_cols, self._get_history_db_data(), cap=caption)

    def db_load(self, args: list[str]) -> None:
        """Loads conversation from history from database."""
        if not args:
            self.io.display_message("Command:Please provide a message ID.")
            return

        try:
            message_id = int(args[0])
        except ValueError:
            self.io.display_message("Command:Invalid ID format. Must be an integer.")
            return

        # First, get the cid for the given message ID
        cid_stmt = select(MessageLogTable.cid).where(MessageLogTable.id == message_id)
        cid_result = self.db.load(MessageLogTable, statement=cid_stmt)
        if not cid_result:
            self.io.display_message(f"Command:No conversation found for ID {message_id}.")
            return

        cid = cid_result[0][0]

        # Now retrieve all messages for this cid ordered by oldest first
        conv_stmt = (
            select(
                MessageLogTable.cid,
                MessageLogTable.author,
                MessageLogTable.flow,
                MessageLogTable.message,
                MessageLogTable.tool_call,
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
                new_history.append(HumanMessage(content=row[3]))
                self.io.display_message(f"User:{row[3]}")
            if row[1] == "ai":
                new_history.append(AIMessage(content=row[3], tool_calls=row[4] if row[4] else []))
                self.io.display_message(f"Assistant:{row[3]}", format_markdown=True) if row[3] else None
            if row[1] == "tool":
                new_history.append(ToolMessage(content=row[3], tool_call_id="unknown_id"))


class CommandProcessor:
    """Class which defines all available user commands and handles their execution."""

    def __init__(self, session: FlowSession) -> None:
        """Init class for user commands execution."""
        self.session = session
        self.io = get_terminal_handler()
        self.db = get_db_handler()
        self.cmd_db = DatabaseCommandProcessor(session)
        self.commands = {}
        self.register_default_commands()

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
        self.register_command("s", self.cmd_save, desc="Save conversation history to markdown")
        # History manipulation
        self.register_command("r", self.cmd_clear, desc="Clear session history")
        self.register_command("f", self.cmd_flow, desc="Change used flow")
        # self.register_command("a", self.cmd_archive, desc="Archive current conversation with optional metadata")
        self.register_command("l", self.cmd_db.db_load, desc="Load conversation using ID")
        self.register_command("b", self.cmd_back, desc="Remove last N turns")
        self.register_command("v", self.cmd_db.db_view, desc="View 10 latest conversations from history db.")
        # self.register_command("e", self.cmd_db_exit, desc="Exit DB view")
        self.register_command("u", self.cmd_db.db_up, desc="Scroll up in DB view")
        self.register_command("d", self.cmd_db.db_down, desc="Scroll down in DB view")

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
                self.io.display_message(f"Unknown command: {cmd}")

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
        self.io.display_message("Command:Memory cleared!")

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
            self.io.display_message(f"Starting {self.session.str_flow_info}")
            self.io.display_message(f"Command:Flow changed to {self.session.flow.config.name}.")

    def cmd_save(self, _: list[str]) -> None:
        """Save current history into a markdown file."""
        path_to_saved_file = save_memory(self.session.chat_history, self.session.flow.config.name)
        self.io.display_message(f"Command:Conversation history saved at '{path_to_saved_file}'.")

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
                self.io.display_message(f"User:{msg.content}")
            if isinstance(msg, AIMessage):
                self.io.display_message(f"Assistant:{msg.content}", format_markdown=True)
            fake_state["messages"].append(msg)
            log_handler.log_message(fake_state)

        # Inform user
        self.io.display_message(f"Command:Removed last {steps} turn(s) and created new conversation history.")

    # def cmd_archive(self, args):
    #     metadata = self._parse_metadata(args)
    #     summary = self.session.summarize()
    #     self.db.archive_conversation(self.session.chat_history, summary, metadata)
    #     self.io.display_message("Conversation archived.")

    # def cmd_load(self, args):
    #     conv_id = args[0] if args else None
    #     if conv_id:
    #         conversation = self.db.load_conversation(conv_id)
    #         self.session.load_history(conversation)
    #         self.io.display_message(f"Loaded conversation {conv_id}")

    # # ... other handlers ...

    # def _parse_metadata(self, args):
    #     metadata = {}
    #     for arg in args:
    #         if "=" in arg:
    #             k, v = arg.split("=", 1)
    #             metadata[k] = v
    #     return metadata
