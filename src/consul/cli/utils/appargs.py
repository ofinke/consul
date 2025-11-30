from collections.abc import Callable

import click
from loguru import logger
from pydantic import BaseModel

from consul.core.config import AvailableFlow


class UserArgs(BaseModel):
    verbose: bool
    quiet: bool
    flow: AvailableFlow
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
    @click.option("--quiet", "-q", is_flag=True, help="Only show warnings and errors")
    @click.option("--flow", "-f", type=str, default="chat", help="Select flow type")
    @click.option("--message", "-m", type=str, default="", help="Write initial message for the flow.")
    @click.option("--cfg-reload", is_flag=True, help="Reloads configuration from defaults.yaml file.")
    def wrapper(*, verbose: bool, quiet: bool, flow: str, message: str, cfg_reload: bool) -> None:
        if verbose and quiet:
            msg = "Cannot use both --verbose and --quiet flags"
            raise click.BadParameter(msg)

        # try to assign flow name to existing flow
        try:
            flow = AvailableFlow(flow)
        except ValueError:
            logger.warning(f"'{flow}' not a name of existing flow, starting 'chat' flow")
            flow = AvailableFlow("chat")

        args = UserArgs(verbose=verbose, quiet=quiet, flow=flow, message=message, cfg_reload=cfg_reload)
        func(args)

    return wrapper
