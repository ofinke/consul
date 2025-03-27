import asyncio

from yaspin import yaspin

from consul.cli_tools.utils.argparsers import CliArgsCritic, cli_args_critic
from consul.core.agents.pycritic.agent import acall_agent
from consul.core.modules.files.load import load_file_content


async def runtime(args: CliArgsCritic) -> None:
    """
    LLM Critic for a CLI interace.

    Input:
        - args: Namespace - arguments passed from the CLI

    Raises:
        - RuntimeErorr - for caught exceptions

    """
    try:
        # start spinner
        spinner = yaspin(color="blue", text="Working")
        spinner.start()

        # load the file
        python_file = load_file_content(args.path)
        spinner.write("> File extracted")

        # call the LLM critic
        first_chunk = True
        async for chunk in acall_agent(data=python_file, instruct=args.instruct):
            # stop spinner with a first chunk
            if first_chunk:
                spinner.stop()
                first_chunk = False
            # Print each chunk without adding a newline character
            print(chunk, end="", flush=True)  # noqa: T201
        # Print a newline after all chunks are printed
        print()  # noqa: T201
    except (FileNotFoundError, OSError) as e:
        msg = f"Error encountered: {e}"
        spinner.stop()
        raise RuntimeError(msg) from e
    except Exception as e:
        msg = f"Unexpected error occured: {e}"
        spinner.stop()
        raise RuntimeError(msg) from e

@cli_args_critic
def main(args: CliArgsCritic) -> None:
    """CLI implementation of the LLM Python critic."""
    asyncio.run(runtime(args=args))


if __name__ == "__main__":
    main()
