import click
from langchain_core.messages import ChatMessage
from loguru import logger

from consul.cli.logs.base import setup_loguru_intercept
from consul.core.config.base import ChatTurn
from consul.core.config.flow import AvailableFlow
from consul.flow.agents.react import ReactAgentFlow
from consul.flow.tasks.chat import ChatTask


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Only show warnings and errors")
def main(*, verbose: bool, quiet: bool) -> None:
    """Interactive CLI chat application."""
    setup_loguru_intercept(verbose=verbose, quiet=quiet)

    # Initialize conversation
    task = ChatTask(AvailableFlow.CHAT)
    memory: list[ChatTurn] = []

    # Welcome message
    click.echo("")
    click.echo(r"   ____                      _ ")
    click.echo(r"  / ___|___  _ __  ___ _   _| |")
    click.echo(r" | |   / _ \| '_ \/ __| | | | |")
    click.echo(r" | |__| (_) | | | \__ \ |_| | |")
    click.echo(r"  \____\___/|_| |_|___/\__,_|_|")
    click.echo("")
    click.echo("Welcome to the Consul CLI! Consul is a set of LLM task/agents designed")
    click.echo("to help with simple problems. It is a hobby project :)")
    click.echo("Type '/quit', '/exit', or press Ctrl+C to end the conversation.")
    click.echo("-" * 76)

    agent = ReactAgentFlow(AvailableFlow.DOCS)

    # Execute with a weather question
    result = agent.execute(
        {"messages": [ChatMessage(role="user", content="What is weather in San Francisco?")]}
    )

    click.echo(f"Final response: {result.messages[-1].content}")

    # try:
    #     while True:
    #         # Get user input
    #         try:
    #             user_input = click.prompt("\nYou", type=str, prompt_suffix=": ")
    #         except click.Abort:
    #             # Handle Ctrl+C gracefully
    #             break

    #         # Check for exit commands
    #         if user_input.lower().strip() in ["/quit", "/exit", "/q"]:
    #             break

    #         # Skip empty inputs
    #         if not user_input.strip():
    #             click.echo("Please enter a message or 'quit' to exit.")
    #             continue

    #         # Add user message to memory
    #         memory.append(ChatMessage(role="user", content=user_input))

    #         try:
    #             # Get LLM response
    #             result = task.execute({"messages": memory})

    #             # Add LLM response to memory
    #             memory.append(result.messages[-1])

    #             # Display response
    #             click.echo(f"\nAssistant: {result.messages[-1].content}")

    #         except Exception as e:  # noqa: BLE001
    #             logger.exception(f"Failed to get response: {e!s}")
    #             # Remove the last user message if processing failed
    #             if memory and memory[-1].role == "human":
    #                 memory.pop()

    # except KeyboardInterrupt:
    #     pass

    # Goodbye message
    click.echo("\n\nTurning off!")
    click.echo("-" * 76)


if __name__ == "__main__":
    main()
