import textwrap

import click
from langchain_core.messages import BaseMessage, ChatMessage
from loguru import logger

from consul.cli.logs.base import setup_loguru_intercept
from consul.cli.utils.commands import Commands
from consul.cli.utils.save import save_memory
from consul.cli.utils.text import (
    MAX_WIDTH,
    print_cli_goodbye,
    print_cli_intro,
    smart_text_wrap,
)
from consul.core.config.flows import AvailableFlow
from consul.flows.agents.react import ReactAgentFlow
from consul.flows.base import BaseFlow
from consul.flows.tasks.chat import ChatTask

FLOWS = {
    "chat": ChatTask(AvailableFlow.CHAT),
    "docs": ReactAgentFlow(AvailableFlow.DOCS),
    "tester": ReactAgentFlow(AvailableFlow.TESTER),
}


class FlowType(click.Choice):
    """Custom choice type for flow selection."""

    def __init__(self) -> None:
        super().__init__(FLOWS.keys(), case_sensitive=False)


class ConsulInterface:
    _active_flow: BaseFlow
    _memory: list[BaseMessage]
    _commands: Commands

    def __init__(self, *, verbose: bool, quiet: bool, flow: str, message: str) -> None:
        # Setup logging
        if verbose and quiet:
            msg = "Cannot use both --verbose and --quiet flags"
            raise click.BadParameter(msg)
        setup_loguru_intercept(verbose=verbose, quiet=quiet)

        # Welcome message
        print_cli_intro(FLOWS.keys())

        # setup variables
        self._init_llm_flow(flow)
        self._memory: list[BaseMessage] = []
        self._commands: Commands = Commands()

        # start main loop
        try:
            self._main_loop(message)
        except KeyboardInterrupt:
            pass

        except Exception as e:
            logger.exception(f"Unexpected error in {flow} flow: {e!s}")
            click.echo(f"Unexpected error: {e!s}", err=True)
            raise click.ClickException(str(e)) from e

        finally:
            print_cli_goodbye()

    def _main_loop(self, init_message: str) -> None:
        while True:
            # Get user input
            try:
                if not init_message:
                    user_input = click.prompt(click.style("\nYou", fg="blue"), type=str, prompt_suffix=": ")
                else:
                    click.echo(f"\nYou: {textwrap.fill(init_message, width=MAX_WIDTH)}")
                    user_input = init_message
                    init_message = ""  # reset message to avoid infinite loop
            except click.Abort:
                # Handle Ctrl+C gracefully
                return

            # Check for exit commands
            if user_input.lower().strip() in self._commands.EXIT:
                return

            # Check for command
            if user_input.lower().strip().startswith("/"):
                system_reply = self._handle_user_command(user_input.lower().strip())
                click.echo("\n" + click.style("Command", fg="red") + f": {system_reply}")
                continue

            # Skip empty inputs
            if not user_input.strip():
                click.echo("\n" + click.style("Command", fg="red") + ": Please enter a message")
                continue

            # Run the flow
            user_message = ChatMessage(role="user", content=user_input)
            self._memory.append(user_message)
            result = self._active_flow.execute({"messages": self._memory})
            # Add response to memory
            assistant_message = result.messages[-1]
            new_history_part = result.messages[len(self._memory) :]
            self._memory.extend(new_history_part)
            # Display response
            click.echo("\n" + click.style("Assistant", fg="green") + ": ")
            click.echo(smart_text_wrap(assistant_message.content))

    def _init_llm_flow(self, flow: str) -> None:
        # Change the active flow
        self._active_flow = FLOWS.get(flow, ChatTask(AvailableFlow.CHAT))

        # Inform the user
        if flow not in FLOWS:
            logger.warning(f"Flow '{flow}' not in available flows ({', '.join(FLOWS)}). Starting default flow.")
        click.echo(
            f"\nStarting '{self._active_flow.config.name}' flow, ver: {self._active_flow.config.version}, {click.style('Description:', fg='magenta')}"
        )
        click.echo(textwrap.fill(self._active_flow.config.description, width=MAX_WIDTH))

    def _handle_user_command(self, command: str) -> str:
        # split command
        order, info = ([*command.split(), "", ""])[:2]

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


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Only show warnings and errors")
@click.option("--flow", "-f", type=FlowType(), default="chat", help="Select flow type")
@click.option("--message", "-m", type=str, default="", help="Write initial message for the flow.")
def main(*, verbose: bool, quiet: bool, flow: str, message: str) -> None:
    ConsulInterface(
        verbose=verbose,
        quiet=quiet,
        flow=flow,
        message=message,
    )


if __name__ == "__main__":
    # Use main() for group structure or main_simple() for single command
    main()
