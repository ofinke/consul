import textwrap

import click
from langchain_core.messages import BaseMessage, ChatMessage
from loguru import logger

from consul.cli.logs.base import setup_loguru_intercept
from consul.cli.utils.text import EXIT_COMMANDS, print_cli_goodbye, print_cli_intro
from consul.core.config.flows import AvailableFlow
from consul.flows.agents.react import ReactAgentFlow
from consul.flows.tasks.chat import ChatTask

FLOWS = {
    "chat": ChatTask(AvailableFlow.CHAT),
    "docs": ReactAgentFlow(AvailableFlow.DOCS),
}


class FlowType(click.Choice):
    """Custom choice type for flow selection."""

    def __init__(self) -> None:
        super().__init__(FLOWS.keys(), case_sensitive=False)


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Only show warnings and errors",
)
@click.option(
    "--flow",
    "-f",
    type=FlowType(),
    default="chat",
    help="Select flow type",
)
@click.option(
    "--message",
    "-m",
    type=str,
    default="",
    help="Write initial message for the flow.",
)
def main(*, verbose: bool, quiet: bool, flow: str, message: str) -> None:
    """Interactive CLI chat application."""
    # Setup logging
    if verbose and quiet:
        msg = "Cannot use both --verbose and --quiet flags"
        raise click.BadParameter(msg)

    setup_loguru_intercept(verbose=verbose, quiet=quiet)

    # Initialize conversation memory
    memory: list[BaseMessage] = []

    # Welcome message
    print_cli_intro(FLOWS.keys())

    # get instance of the flow
    flow_instance = FLOWS.get(flow, ChatTask(AvailableFlow.CHAT))

    # print flow intro
    click.echo(f"\nStarting '{flow}' flow, ver: {flow_instance.config.version}")
    wrapped_description = textwrap.fill(flow_instance.config.description, width=76)
    click.echo(f"{wrapped_description}\n")

    try:
        while True:
            # Get user input
            try:
                if not message:
                    user_input = click.prompt("\nYou", type=str, prompt_suffix=": ")
                    click.echo()
                else:
                    click.echo(f"\nYou: {message}")
                    user_input = message
                    message = ""  # reset message to avoid infinite loop
            except click.Abort:
                # Handle Ctrl+C gracefully
                break

            # Check for exit commands
            if user_input.lower().strip() in EXIT_COMMANDS:
                break

            # Skip empty inputs
            if not user_input.strip():
                click.echo("Please enter a message or use /quit to exit.")
                continue

            # Run the flow
            user_message = ChatMessage(role="user", content=user_input)
            memory.append(user_message)
            result = flow_instance.execute({"messages": memory})
            # Add response to memory
            assistant_message = result.messages[-1]
            memory.append(assistant_message)
            # Display response
            click.echo(f"\nAssistant: {assistant_message.content}")

    except KeyboardInterrupt:
        pass

    except Exception as e:
        logger.exception(f"Unexpected error in {flow} flow: {e!s}")
        click.echo(f"Unexpected error: {e!s}", err=True)
        raise click.ClickException(str(e)) from e

    finally:
        print_cli_goodbye()


if __name__ == "__main__":
    # Use main() for group structure or main_simple() for single command
    main()
