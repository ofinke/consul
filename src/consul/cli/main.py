import click
from loguru import logger

from .logging.base import setup_logging


# Example CLI command
@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Only show warnings and errors")
def main(*, verbose: bool, quiet: bool) -> None:
    """Example CLI application."""
    setup_logging(verbose=verbose, quiet=quiet)

    # Your app logic here
    logger.info("Application started")
    logger.debug("Debug information")
    logger.success("Operation completed successfully")
    logger.warning("This is a warning")
    logger.error("This is an error")


if __name__ == "__main__":
    main()
