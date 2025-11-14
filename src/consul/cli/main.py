import click
from loguru import logger

from consul.cli.utils.commands import Commands
from consul.cli.utils.save import save_memory
from consul.cli.utils.text import TerminalHandler, get_terminal_handler
from consul.cli.utils.user_args import UserArgs, consul_user_args
from consul.core.config.flows import AvailableFlow
from consul.flows.session import FlowSession


class CommandInterrupt(BaseException):
    """Runtime interrupt from user command."""


class ConsulInterface:
    """Class representing flow of the consul cli interface."""

    io: TerminalHandler
    session: FlowSession | None = None
    _commands: Commands
    user_args: UserArgs

    def __init__(self, user_args: UserArgs) -> None:
        """Setup console interface state."""
        self.io = get_terminal_handler()

        # Determine log level
        if user_args.quiet:
            level = "WARNING"
        elif user_args.verbose:
            level = "DEBUG"
        else:
            level = "INFO"

        logger.remove()
        logger.add(self.io.display_loguru_message, level=level, format="{message}")

        # setup variables
        self.user_args = user_args
        self._commands: Commands = Commands()

    def start_interface(self) -> None:
        # Start session
        self.session = FlowSession(self.user_args.flow)

        # Welcome message
        self.io.echo_intro([key.value for key in self.session.available_flows])
        self.io.display_message(f"Starting {self.session.str_flow_info}")

        # start main loop
        try:
            self._main_loop()

        # handle exit program via keyboard or command interruption
        except (KeyboardInterrupt, CommandInterrupt):
            pass

        # handle unexpected exceptions
        except Exception as e:
            logger.exception(f"Unexpected error in {self.user_args.flow} flow: {e!s}")
            raise click.ClickException(str(e)) from e

        # cleanup
        finally:
            self.io.echo_goodbye()
            self.io.stop_spinner()

    def _main_loop(self) -> None:
        while True:
            # Get user input
            try:
                if not self.user_args.message:
                    user_input = self.io.prompt_user_input()
                else:
                    self.io.display_message(f"User: {self.user_args.message}")
                    user_input = self.user_args.message
                    self.user_args.message = ""  # reset message to avoid infinite loop
            except click.Abort:
                # Handle Ctrl+C gracefully
                return

            # Check for command
            if user_input.lower().strip().startswith("/"):
                system_reply = self._handle_user_command(user_input.lower().strip())
                self.io.display_message(f"Command:{system_reply}")
                continue

            # Skip empty inputs
            if not user_input.strip():
                self.io.display_message("Command:Please enter a message")
                continue

            # Run the flow
            self.io.start_spinner()

            # post user message
            response = self.session.post_message(user_input)

            # Display response
            self.io.stop_spinner()
            self.io.display_message(f"Assistant:{response}", format_markdown=True)

    def _handle_user_command(self, command: str) -> str:
        """Private method for handling user commands starting with '/' character."""
        # split command
        order, info = ([*command.split(), "", ""])[:2]

        # Exit app
        if order in self._commands.EXIT:
            raise CommandInterrupt

        # clear chat history
        if order in self._commands.RESET:
            self.session.clear_history()
            return "Memory cleared!"

        # change used flow
        if order in self._commands.FLOW:
            try:
                run_this_flow = AvailableFlow(info)
            except ValueError:
                logger.warning(f"'{info}' not a name of existing flow, starting 'chat' flow")
                run_this_flow = AvailableFlow("chat")
            finally:
                self.session.change_flow(run_this_flow)
                self.io.display_message(f"Starting {self.session.str_flow_info}")
            return f"Flow changed to {self.session.flow.config.name}."

        # save data to markdown
        if order in self._commands.SAVE:
            path_to_saved_file = save_memory(self.session.chat_history, self.session.flow.config.name)
            return f"Conversation history saved at '{path_to_saved_file}'"
        return "Unknown command!"


@consul_user_args
def main(user_args: UserArgs) -> None:
    while True:
        cli = ConsulInterface(user_args)
        try:
            cli.start_interface()
            break  # Exit if interface finishes normally
        except click.ClickException:
            restart = input("An error occurred. Restart interface? (y/n): ").strip().lower()
            if restart != "y":
                break


if __name__ == "__main__":
    # Use main() for group structure or main_simple() for single command
    main()
