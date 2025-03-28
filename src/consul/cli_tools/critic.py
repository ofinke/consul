import asyncio

import click
from yaspin import yaspin

from consul.cli_tools.utils.argparsers import CliArgsCritic, cli_args_critic
from consul.core.agents.pycritic.agent import acall_agent
from consul.core.modules.files.load import load_file_content


async def runtime(args: CliArgsCritic) -> None:
    """
    LLM Critic for a CLI interace using click for output.

    Input:
        - args: Namespace - arguments passed from the CLI

    Raises:
        - RuntimeErorr - for caught exceptions

    """
    spinner = None
    try:
        # start spinner
        spinner = yaspin(color="blue", text="Working")
        spinner.start()

        # load the file
        python_file = load_file_content(args.path)
        spinner.write("> File extracted")  # yaspin handles its own output

        # call the LLM critic
        first_chunk = True
        async for chunk in acall_agent(data=python_file, instruct=args.instruct):
            # stop spinner with a first chunk
            if first_chunk:
                if spinner:
                    spinner.stop()
                first_chunk = False
            click.echo(chunk, nl=False)
        # Use click.echo() with no arguments to print a final newline
        click.echo()

    # Exception handling
    except (FileNotFoundError, OSError) as e:
        msg = f"Error encountered: {e}"
        if spinner and spinner.is_active:
            spinner.stop()
        raise RuntimeError(msg) from e
    except Exception as e:
        msg = f"Unexpected error occured: {e}"
        if spinner and spinner.is_active:
            spinner.stop()
        raise RuntimeError(msg) from e
    finally:
        # Ensure spinner is stopped if it was active and the loop didn't start/finish
        if spinner and spinner.is_active and first_chunk:
            spinner.stop()


@cli_args_critic
def main(args: CliArgsCritic) -> None:
    """CLI implementation of the LLM Python critic."""
    asyncio.run(runtime(args=args))


if __name__ == "__main__":
    main()
