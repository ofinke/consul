import click
from langchain_core.messages import BaseMessage, ChatMessage
from loguru import logger

from consul.cli.utils.commands import Commands
from consul.cli.utils.save import save_memory
from consul.cli.utils.text import TerminalHandler, smart_text_wrap
from consul.cli.utils.user_args import UserArgs, consul_user_args
from consul.core.config.flows import AvailableFlow
from consul.flows.agents.react import ReactAgentFlow
from consul.flows.base import BaseFlow
from consul.flows.tasks.chat import ChatTask

FLOWS = {
    "chat": ChatTask(AvailableFlow.CHAT),
    "docs": ReactAgentFlow(AvailableFlow.DOCS),
    "tester": ReactAgentFlow(AvailableFlow.TESTER),
}


class CommandInterrupt(BaseException):
    """Runtime interrupt from user command."""


class ConsulInterface:
    _active_flow: BaseFlow
    _memory: list[BaseMessage]
    _commands: Commands
    _user_args: UserArgs

    def __init__(self, user_args: UserArgs) -> None:
        # Determine log level
        if user_args.quiet:
            level = "WARNING"
        elif user_args.verbose:
            level = "DEBUG"
        else:
            level = "INFO"

        logger.remove()
        logger.add(TerminalHandler.echo_loguru_message, level=level, format="{message}")

        # setup variables
        self._user_args = user_args
        self._memory: list[BaseMessage] = []
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
            click.echo(f"Unexpected error: {e!s}", err=True)
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
                    user_input = click.prompt(click.style("\nYou", fg="blue"), type=str, prompt_suffix=": ")
                else:
                    click.echo(f"\nYou: {smart_text_wrap(self._user_args.message)}")
                    user_input = self._user_args.message
                    self._user_args.message = ""  # reset message to avoid infinite loop
            except click.Abort:
                # Handle Ctrl+C gracefully
                return

            # Check for command
            if user_input.lower().strip().startswith("/"):
                system_reply = self._handle_user_command(user_input.lower().strip())
                click.echo("\n" + click.style("Command", fg="yellow") + f": {system_reply}")
                continue

            # Skip empty inputs
            if not user_input.strip():
                click.echo("\n" + click.style("Command", fg="yellow") + ": Please enter a message")
                continue

            # Run the flow
            TerminalHandler.start_spinner()
            user_message = ChatMessage(role="user", content=user_input)
            self._memory.append(user_message)

            result = self._active_flow.execute({"messages": self._memory})

            # Add response to memory
            assistant_message = result.messages[-1]
            new_history_part = result.messages[len(self._memory) :]
            self._memory.extend(new_history_part)

            # Display response
            TerminalHandler.stop_spinner()
            click.echo("\n" + click.style("AI", fg="green") + ": ")
            click.echo(smart_text_wrap(assistant_message.content))

    def _init_llm_flow(self, flow: str) -> None:
        # Change the active flow
        self._active_flow = FLOWS.get(flow, ChatTask(AvailableFlow.CHAT))

        # Inform the user
        if flow not in FLOWS:
            logger.warning(f"Flow '{flow}' not in available flows ({', '.join(FLOWS)}). Starting default flow.")
        click.echo(
            smart_text_wrap(
                f"\nStarting '{self._active_flow.config.name}' flow, ver: {self._active_flow.config.version}, {click.style('Description', fg='magenta')}: {self._active_flow.config.description}"
            )
        )

    def _handle_user_command(self, command: str) -> str:
        # split command
        order, info = ([*command.split(), "", ""])[:2]

        if order in self._commands.EXIT:
            raise CommandInterrupt

        if order in self._commands.RESET:
            self._memory = []
            return "Memory cleared!"

        if order in self._commands.FLOW:
            self._init_llm_flow(info)
            self._memory = []
            return f"Flow changed to {self._active_flow.config.name} and memory cleared."

        if order in self._commands.SAVE:
            path_to_saved_file = save_memory(self._memory)
            return f"Conversation history saved in {path_to_saved_file}"

        return click.style("Unknown command!", fg="red")


@consul_user_args
def main(user_args: UserArgs) -> None:
    cli = ConsulInterface(user_args)
    cli.start_interface()


if __name__ == "__main__":
    # Use main() for group structure or main_simple() for single command
    main()
