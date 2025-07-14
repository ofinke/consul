import textwrap

import click
from langchain_core.messages import BaseMessage, ChatMessage
from loguru import logger

from consul.cli.logs.base import setup_loguru_intercept
from consul.cli.utils.text import EXIT_COMMANDS, print_cli_goodbye, print_cli_intro
from consul.core.config.flow import AvailableFlow
from consul.flows.agents.react import ReactAgentFlow
from consul.flows.tasks.chat import ChatTask


class FlowType(click.Choice):
    """Custom choice type for flow selection."""

    def __init__(self) -> None:
        super().__init__(["chat", "docs"], case_sensitive=False)


def handle_chat_flow(memory: list[BaseMessage]) -> None:
    """Handle interactive chat flow."""
    task = ChatTask(AvailableFlow.CHAT)
    _handle_interactive_flow(task, memory, "chat")


def handle_docs_flow(memory: list[BaseMessage]) -> None:
    """Handle interactive documentation flow."""
    agent = ReactAgentFlow(AvailableFlow.DOCS)
    _handle_interactive_flow(agent, memory, "docs")


def _handle_interactive_flow(
    flow_instance: ChatTask | ReactAgentFlow, memory: list[BaseMessage], flow_name: str
) -> None:
    """
    Handle interactive flow for both chat and docs.

    Args:
        flow_instance: The flow instance (ChatTask or ReactAgentFlow)
        memory: List to store conversation messages
        flow_name: Name of the flow for logging purposes
    """
    click.echo(f"\nStarting '{flow_name}' flow, ver: {flow_instance.config.version}")
    wrapped_description = textwrap.fill(flow_instance.config.description, width=76)
    click.echo(f"{wrapped_description}\n")

    try:
        while True:
            # Get user input
            try:
                user_input = click.prompt("\nYou", type=str, prompt_suffix=": ")
                click.echo()
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

            # Process user input
            if not _process_user_message(flow_instance, memory, user_input, flow_name):
                break

    except KeyboardInterrupt:
        pass


def _process_user_message(
    flow_instance: ChatTask | ReactAgentFlow,
    memory: list[BaseMessage],
    user_input: str,
    flow_name: str,
) -> bool:
    """
    Process a user message and update memory.

    Args:
        flow_instance: The flow instance to execute
        memory: List to store conversation messages
        user_input: User's input message
        flow_name: Name of the flow for logging purposes

    Returns:
        bool: True if processing was successful, False if should exit.
    """
    # Add user message to memory
    user_message = ChatMessage(role="user", content=user_input)
    memory.append(user_message)

    try:
        # Get response from the flow
        result = flow_instance.execute({"messages": memory})

        # Add response to memory
        assistant_message = result.messages[-1]
        memory.append(assistant_message)

        # Display response
        click.echo(f"\nAssistant: {assistant_message.content}")

    except Exception as e:
        logger.exception(f"Failed to get response from {flow_name} flow: {e!s}")
        click.echo(f"Error: {e!s}", err=True)

        # Remove the last user message if processing failed
        if memory and memory[-1] == user_message:
            memory.pop()

    return True


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Only show warnings and errors")
@click.option(
    "--flow",
    "-f",
    type=FlowType(),
    default="chat",
    help="Select flow type (chat or docs)",
)
# TODO: finish setting up this variable
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
    print_cli_intro()

    try:
        # Route to appropriate flow
        if flow == "docs":
            handle_docs_flow(memory)
        else:  # default to chat
            handle_chat_flow(memory)
    except Exception as e:
        logger.exception(f"Unexpected error in {flow} flow: {e!s}")
        click.echo(f"Unexpected error: {e!s}", err=True)
        raise click.ClickException(str(e)) from e
    finally:
        print_cli_goodbye()


if __name__ == "__main__":
    # Use main() for group structure or main_simple() for single command
    main()
