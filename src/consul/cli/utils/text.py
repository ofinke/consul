import re
import textwrap

import click

EXIT_COMMANDS = {"/q"}
RESET_COMMANDS = {"/r"}
MAX_WIDTH = 100


def print_cli_intro(flows: list[str]) -> None:
    """Prints introductory text to CLI interface of Consul."""
    intro_message = f"Welcome to the Consul CLI! Consul contains set of simple LLM flows and agents for solving small daily problems. Type {', '.join(EXIT_COMMANDS)}, or press Ctrl+C to end the conversation. Reset history with {', '.join(RESET_COMMANDS)}. Flow can be selected by calling consul with the '--flow' '-f' flag, available flows are: {', '.join(flows)}"  # noqa: E501

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
    click.echo(click.style("\n\nSigning off! Bye ツ!", fg="cyan"))
    click.echo(click.style("Consul code available at https://github.com/ofinke/consul under MIT licence.", fg="cyan"))
    click.echo(click.style("-" * MAX_WIDTH, fg="cyan"))


def smart_text_wrap(text: str) -> str:
    """Wrap text line by line, only wrapping lines that exceed the width. Preserves list formatting and indentation."""
    lines = text.split("\n")
    wrapped_lines = []

    for line in lines:
        if len(line) <= MAX_WIDTH:
            wrapped_lines.append(line)
        else:
            # Detect list items and their indentation
            list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+", line)

            if list_match:
                # Handle list items
                indent = list_match.group(1)  # Leading whitespace
                marker = list_match.group(2)  # List marker (-, *, +, or number.)

                # Calculate the hanging indent (indent + marker + space)
                hanging_indent = len(indent) + len(marker) + 1

                wrapped = textwrap.fill(
                    line, width=MAX_WIDTH, initial_indent="", subsequent_indent=" " * hanging_indent
                )
                wrapped_lines.append(wrapped)
            else:
                # Handle regular lines - preserve any leading whitespace
                leading_space_match = re.match(r"^(\s*)", line)
                leading_space = leading_space_match.group(1) if leading_space_match else ""

                wrapped = textwrap.fill(line, width=MAX_WIDTH, initial_indent="", subsequent_indent=leading_space)
                wrapped_lines.append(wrapped)

    return "\n".join(wrapped_lines)
