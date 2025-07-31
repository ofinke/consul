import click
from langchain_core.messages import BaseMessage, ChatMessage
from loguru import logger

from consul.cli.utils.commands import Commands
from consul.cli.utils.save import save_memory
from consul.cli.utils.text import TerminalHandler
from consul.cli.utils.user_args import UserArgs, consul_user_args
from consul.core.config.flows import AvailableFlow
from consul.flows.agents.react import ReactAgentFlow
from consul.flows.base import BaseFlow
from consul.flows.tasks.chat import ChatTask

FLOWS = {
    "chat": ChatTask(AvailableFlow.CHAT),
    "coder": ReactAgentFlow(AvailableFlow.CODER),
    "tester": ReactAgentFlow(AvailableFlow.TESTER),
}


class CommandInterrupt(BaseException):
    """Runtime interrupt from user command."""


class ConsulInterface:
    """Class representing flow of the consul cli interface."""

    _active_flow: BaseFlow
    _chat_history: list[BaseMessage]
    _commands: Commands
    _user_args: UserArgs

    def __init__(self, user_args: UserArgs) -> None:
        """Setup console interface state."""
        # Determine log level
        if user_args.quiet:
            level = "WARNING"
        elif user_args.verbose:
            level = "DEBUG"
        else:
            level = "INFO"

        logger.remove()
        logger.add(TerminalHandler.display_loguru_message, level=level, format="{message}")

        # setup variables
        self._user_args = user_args
        self._chat_history: list[BaseMessage] = []
        self._commands: Commands = Commands()

    def start_interface(self) -> None:
        # Welcome message
        TerminalHandler.echo_intro(FLOWS.keys())

        # initiate first flow
        self._init_llm_flow(self._user_args.flow)

        # start main loop
        try:
            self._main_loop()

        # handle exit program via keyboard or command interruption
        except (KeyboardInterrupt, CommandInterrupt):
            pass

        # handle unexpected exceptions
        except Exception as e:
            logger.exception(f"Unexpected error in {self._user_args.flow} flow: {e!s}")
            raise click.ClickException(str(e)) from e

        # cleanup
        finally:
            TerminalHandler.echo_goodbye()
            TerminalHandler.stop_spinner()

    def _main_loop(self) -> None:
        while True:
            # Get user input
            try:
                if not self._user_args.message:
                    user_input = TerminalHandler.prompt_user_input()
                else:
                    TerminalHandler.display_message(f"User: {self._user_args.message}")
                    user_input = self._user_args.message
                    self._user_args.message = ""  # reset message to avoid infinite loop
            except click.Abort:
                # Handle Ctrl+C gracefully
                return

            # Check for command
            if user_input.lower().strip().startswith("/"):
                system_reply = self._handle_user_command(user_input.lower().strip())
                TerminalHandler.display_message(f"Command:{system_reply}")
                continue

            # Skip empty inputs
            if not user_input.strip():
                TerminalHandler.display_message("Command:Please enter a message")
                continue

            # Run the flow
            TerminalHandler.start_spinner()

            # prepare history and call the flow
            user_message = ChatMessage(role="user", content=user_input)
            self._chat_history.append(user_message)
            result = self._active_flow.execute({"messages": self._chat_history})

            # Process response
            assistant_message = result.messages[-1]
            new_history_part = result.messages[len(self._chat_history) :]
            self._chat_history.extend(new_history_part)

            # Display response
            TerminalHandler.stop_spinner()
            TerminalHandler.display_message(f"Assistant:{assistant_message.content}", format_markdown=True)

    def _init_llm_flow(self, flow: str) -> None:
        # Change the active flow
        self._active_flow = FLOWS.get(flow, ChatTask(AvailableFlow.CHAT))

        # Inform the user
        if flow not in FLOWS:
            logger.warning(f"Flow '{flow}' not in available flows ({', '.join(FLOWS)}). Starting default flow.")
        TerminalHandler.display_message(
            f"Starting '{self._active_flow.config.name}' flow, ver: {self._active_flow.config.version}; {self._active_flow.config.description}"  # noqa: E501
        )

    def _handle_user_command(self, command: str) -> str:
        """Private method for handling user commands starting with '/' character."""
        # split command
        order, info = ([*command.split(), "", ""])[:2]
        # Exit app
        if order in self._commands.EXIT:
            raise CommandInterrupt
        # clear chat history
        if order in self._commands.RESET:
            self._chat_history = []
            return "Memory cleared!"
        # change used flow
        if order in self._commands.FLOW:
            self._init_llm_flow(info)
            self._chat_history = []
            return f"Flow changed to {self._active_flow.config.name} and memory cleared."
        # save data to markdown
        if order in self._commands.SAVE:
            path_to_saved_file = save_memory(self._chat_history, self._active_flow.config.name)
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
