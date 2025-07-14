import click

EXIT_COMMANDS = {"/quit", "/exit", "/q"}
PROMPT_SEPARATOR = "-" * 76


def print_cli_intro() -> None:
    """Prints introductory text to CLI interface of Consul."""
    click.echo("")
    click.echo(r"   ____                      _ ")
    click.echo(r"  / ___|___  _ __  ___ _   _| |")
    click.echo(r" | |   / _ \| '_ \/ __| | | | |")
    click.echo(r" | |__| (_) | | | \__ \ |_| | |")
    click.echo(r"  \____\___/|_| |_|___/\__,_|_|")
    click.echo("")
    click.echo("Welcome to the Consul CLI! Consul is a set of LLM task/agents designed")
    click.echo("to help with simple problems. It is a hobby project :)")
    click.echo(f"Type {', '.join(EXIT_COMMANDS)}, or press Ctrl+C to end the conversation.")
    click.echo("-" * 76)


def print_cli_goodbye() -> None:
    """Display goodbye message."""
    click.echo("\n\nTurning off!")
    click.echo(PROMPT_SEPARATOR)
