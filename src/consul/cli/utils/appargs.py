from collections.abc import Callable

import click
from pydantic import BaseModel


class UserArgs(BaseModel):
    verbose: bool
    flow: str
    message: str
    cfg_reload: bool


# TODO: Add commands for basic config managment
#   --cfg-defaults - cleares all config tables and reloads them with default values
#   --cfg-update - loads all config yamls and stores them again (updating existing, adding new)
#   --cfg-add (file) - add a new yaml file into config
# But before doing it, think a little bit deeper how and what configs I want to store in db. For example flows?


def consul_user_args(func: Callable[[UserArgs], None]) -> Callable[..., None]:
    """Wrapper which converts click options into a pydantic object."""

    # Define click commands according to the equivalent pydantic model
    @click.command()
    @click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
    @click.option("--flow", "-f", type=str, default="chat", help="Select flow type")
    @click.option("--message", "-m", type=str, default="", help="Write initial message for the flow.")
    @click.option("--cfg-reload", is_flag=True, help="Reloads configuration from defaults.yaml file.")
    def wrapper(*, verbose: bool, flow: str, message: str, cfg_reload: bool) -> None:
        args = UserArgs(verbose=verbose, flow=flow, message=message, cfg_reload=cfg_reload)
        func(args)

    return wrapper
