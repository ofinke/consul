import click

from consul.cli.logging.base import setup_loguru_intercept
from consul.tasks.ask import AskTask


# Example CLI command
@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Only show warnings and errors")
@click.option("--message", "-m", help="Instructions for the LLM")
def main(*, verbose: bool, quiet: bool, message: str) -> None:
    """Example CLI application."""
    setup_loguru_intercept(verbose=verbose, quiet=quiet)

    # Your app logic here
    task = AskTask()

    result = task.execute(
        {
            "text": message,
        }
    )

    click.echo(f"\nLLM Answer:\n\n{result.llm_response}")


if __name__ == "__main__":
    main()
