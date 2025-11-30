import click
from loguru import logger

from consul.cli.commands import CommandProcessor
from consul.cli.exceptions import CommandInterrupt
from consul.cli.terminal import TerminalHandler, get_terminal_handler
from consul.cli.utils.appargs import UserArgs, consul_user_args
from consul.core.config import store_defaults
from consul.flows.session import FlowSession


class ConsulInterface:
    """Class representing flow of the consul cli interface."""

    io: TerminalHandler
    session: FlowSession
    commands: CommandProcessor
    user_args: UserArgs

    def __init__(self, user_args: UserArgs) -> None:
        """Setup console interface state."""
        # Initialize interface
        self.user_args = user_args
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

        self.session = FlowSession(self.user_args.flow)
        self.commands = CommandProcessor(self.session)

    def start_interface(self) -> None:
        # Welcome message
        self.io.echo_intro([key.value for key in self.session.available_flows])
        self.io.display_message(f"Command: Starting {self.session.str_flow_info}")

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
                self.commands.process_input(user_input.lower().strip())
                continue

            # Skip empty inputs
            if not user_input.strip():
                self.io.display_message("Command: Please enter a message")
                continue

            # Run the flow
            self.io.start_spinner()

            # post user message
            response = self.session.post_message(user_input)

            # Display response
            self.io.stop_spinner()
            self.io.display_message(f"Assistant: {response}")


@consul_user_args
def main(user_args: UserArgs) -> None:
    store_defaults(force_refresh=user_args.cfg_reload)
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
