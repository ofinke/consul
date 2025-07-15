import click

EXIT_COMMANDS = {"/quit", "/exit", "/q"}
MAX_WIDTH = 99


def print_cli_intro(flows: list[str]) -> None:
    """Prints introductory text to CLI interface of Consul."""
    click.echo("")
    click.echo(r"   ____                      _ ")
    click.echo(r"  / ___|___  _ __  ___ _   _| |")
    click.echo(r" | |   / _ \| '_ \/ __| | | | |")
    click.echo(r" | |__| (_) | | | \__ \ |_| | |")
    click.echo(r"  \____\___/|_| |_|___/\__,_|_|")
    click.echo("")
    click.echo("Welcome to the Consul CLI! Consul is a set of LLM flows designed to help with simple problems.")
    click.echo(f"Type {', '.join(EXIT_COMMANDS)}, or press Ctrl+C to end the conversation.")
    click.echo(f"Flow can be selected using the '--flow' '-f' flag, available flows are: {', '.join(flows)}")
    click.echo("-" * MAX_WIDTH)


def print_cli_goodbye() -> None:
    """Display goodbye message."""
    click.echo("\nTurning off!")
    click.echo("Consul project code available at https://github.com/ofinke/consul under MIT licence.")
    click.echo("-" * MAX_WIDTH)
