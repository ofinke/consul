import click
from loguru import logger

from consul.cli.logging.base import setup_loguru_intercept
from consul.tasks.summarize import SummarizeTextTask


# Example CLI command
@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Only show warnings and errors")
def main(*, verbose: bool, quiet: bool) -> None:
    """Example CLI application."""
    setup_loguru_intercept(verbose=verbose, quiet=quiet)

    # Your app logic here
    task = SummarizeTextTask()

    result = task.execute(
        {
            "text": "High-harmonic generation (HHG) is a non-linear process during which a target (gas, plasma, solid or liquid sample) is illuminated by an intense laser pulse. Under such conditions, the sample will emit the high order harmonics of the generation beam (above the fifth harmonic). Due to the coherent nature of the process, high-harmonics generation is a prerequisite of attosecond physics. ",
            "max_length": 100,
        }
    )

    logger.info(result["summary"])


if __name__ == "__main__":
    main()
