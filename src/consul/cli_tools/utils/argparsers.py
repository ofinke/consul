from collections.abc import Callable

import click
from pydantic import BaseModel


class CliArgsCritic(BaseModel):
    path: str
    instruct: str = ""


def cli_args_critic(func: Callable[[CliArgsCritic], None]) -> Callable[..., None]:
    """Wrapper defining input parameters for CLI implementation fro pycritic."""

    # Define click commands according to the equivalent pydantic model
    @click.command()
    @click.option(
        "-p",
        "--path",
        type=str,
        required=True,
        help="Relative path to the file",
    )
    @click.option(
        "-i",
        "--instruct",
        type=str,
        required=False,
        default="",
        help="Additional instructions for the LLM",
    )
    def wrapper(path: str, instruct: str) -> CliArgsCritic:
        args = CliArgsCritic(path=path, instruct=instruct)
        func(args)

    return wrapper
