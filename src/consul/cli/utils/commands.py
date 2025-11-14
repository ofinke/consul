from collections.abc import Callable

from loguru import logger

from consul.cli.exceptions import CommandInterrupt
from consul.cli.utils.save import save_memory
from consul.cli.utils.text import get_terminal_handler
from consul.core.config.flows import AvailableFlow
from consul.flows.session import FlowSession


class CommandProcessor:
    def __init__(self, session: FlowSession):
        self.session = session
        self.io = get_terminal_handler()
        # self.db = db
        self.commands = {}
        self.register_default_commands()

    def register_command(self, name: str, handler: Callable, aliases: list[str] | None = None, desc: str = "") -> None:
        for cmd in [name] + (aliases or []):
            self.commands[cmd] = {"handler": handler, "help": desc}

    def register_default_commands(self) -> None:
        self.register_command("h", self.cmd_help, aliases=["help"], desc="Show list of commands")
        self.register_command("q", self.cmd_exit, aliases=["quit"], desc="Exit the application")
        self.register_command("s", self.cmd_save, desc="Save conversation history to markdown")
        self.register_command("r", self.cmd_clear, desc="Clear history")
        self.register_command("f", self.cmd_flow, desc="Change used flow")
        # TODO:
        # self.register_command("a", self.cmd_archive, help_text="Archive current conversation with optional metadata")
        # self.register_command("l", self.cmd_load, help_text="Load conversation by ID")
        # self.register_command("b", self.cmd_back, help_text="Remove last N turns")
        # self.register_command("db", self.cmd_db_view, help_text="Enter database view mode")
        # self.register_command("e", self.cmd_db_exit, help_text="Exit DB view")
        # self.register_command("u", self.cmd_db_up, help_text="Scroll up in DB view")
        # self.register_command("d", self.cmd_db_down, help_text="Scroll down in DB view")

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

    # Example command handlers
    def cmd_help(self, _: list[str]) -> None:
        cmds = "\n".join(f"/{cmd} - {meta['help']}" for cmd, meta in self.commands.items())
        self.io.display_message(cmds)

    def cmd_exit(self, _: list[str]) -> None:
        raise CommandInterrupt

    def cmd_clear(self, _: list[str]) -> None:
        self.session.clear_history()
        self.io.display_message("Command:Memory cleared!")

    def cmd_flow(self, args: list[str]) -> None:
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
        path_to_saved_file = save_memory(self.session.chat_history, self.session.flow.config.name)
        self.io.display_message(f"Command:Conversation history saved at '{path_to_saved_file}'.")

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

    # def cmd_back(self, args):
    #     steps = int(args[0]) if args else 1
    #     self.session.remove_last_turns(steps)
    #     self.io.display_message(f"Removed last {steps} turns.")

    # # ... other handlers ...

    # def _parse_metadata(self, args):
    #     metadata = {}
    #     for arg in args:
    #         if "=" in arg:
    #             k, v = arg.split("=", 1)
    #             metadata[k] = v
    #     return metadata
