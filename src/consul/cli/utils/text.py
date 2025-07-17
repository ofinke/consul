import textwrap

import click

EXIT_COMMANDS = {"/quit", "/exit", "/q"}
MAX_WIDTH = 100


def print_cli_intro(flows: list[str]) -> None:
    """Prints introductory text to CLI interface of Consul."""
    intro_message = f"Welcome to the Consul CLI! Consul contains set of simple LLM flows and agents for solving small daily problems. Type {', '.join(EXIT_COMMANDS)}, or press Ctrl+C to end the conversation. Flow can be selected by calling consul with the '--flow' '-f' flag, available flows are: {', '.join(flows)}"  # noqa: E501

    click.echo("")
    click.echo(click.style(f"{18 * '░'}   █████████   {40 * '░'}   ████   {16 * '░'}", fg="cyan"))
    click.echo(click.style(f"{18 * ' '}  ███░░░░░███                                            ░░███ ", fg="cyan"))
    click.echo(click.style(f"{18 * ' '} ███     ░░░    ██████   ████████     █████   █████ ████  ░███ ", fg="cyan"))
    click.echo(click.style(f"{18 * ' '}░███           ███░░███ ░░███░░███   ███░░   ░░███ ░███   ░███ ", fg="cyan"))
    click.echo(click.style(f"{18 * ' '}░███          ░███ ░███  ░███ ░███  ░░█████   ░███ ░███   ░███ ", fg="cyan"))
    click.echo(click.style(f"{18 * ' '}░░███     ███ ░███ ░███  ░███ ░███   ░░░░███  ░███ ░███   ░███ ", fg="cyan"))
    click.echo(click.style(f"{18 * ' '} ░░█████████  ░░██████   ████ █████  ██████   ░░████████  █████", fg="cyan"))
    click.echo(
        click.style(
            f"{17 * '░'}   ░░░░░░░░░    ░░░░░░   ░░░░ ░░░░░  ░░░░░░     ░░░░░░░░  ░░░░░   {16 * '░'}", fg="cyan"
        )
    )
    click.echo("")
    click.echo(click.style(textwrap.fill(intro_message, width=MAX_WIDTH), fg="cyan"))
    click.echo(click.style("-" * MAX_WIDTH, fg="cyan"))


def print_cli_goodbye() -> None:
    """Display goodbye message."""
    click.echo("\nTurning off!")
    click.echo("Consul project code available at https://github.com/ofinke/consul under MIT licence.")
    click.echo(click.style("-" * MAX_WIDTH, fg="cyan"))
