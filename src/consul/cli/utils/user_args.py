from collections.abc import Callable

import click
from pydantic import BaseModel


class UserArgs(BaseModel):
    verbose: bool
    quiet: bool
    flow: str
    message: str


def consul_user_args(func: Callable[[UserArgs], None]) -> Callable[..., None]:
    """Wrapper which converts click options into a pydantic object."""

    # Define click commands according to the equivalent pydantic model
    @click.command()
    @click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
    @click.option("--quiet", "-q", is_flag=True, help="Only show warnings and errors")
    @click.option("--flow", "-f", type=str, default="chat", help="Select flow type")
    @click.option("--message", "-m", type=str, default="", help="Write initial message for the flow.")
    def wrapper(*, verbose: bool, quiet: bool, flow: str, message: str) -> None:
        if verbose and quiet:
            msg = "Cannot use both --verbose and --quiet flags"
            raise click.BadParameter(msg)

        args = UserArgs(verbose=verbose, quiet=quiet, flow=flow, message=message)
        func(args)

    return wrapper
