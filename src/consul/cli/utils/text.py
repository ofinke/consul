import re
import textwrap

import click

from consul.cli.utils.commands import Commands

EXIT_COMMANDS = {"/q"}
RESET_COMMANDS = {"/r"}
MAX_WIDTH = 100


def print_cli_intro(flows: list[str]) -> None:
    """Prints introductory text to CLI interface of Consul."""
    intro_message = f"Welcome to the Consul CLI! Consul contains set of simple LLM flows and agents for solving small daily problems. Flow can be selected by starting consul with the '--flow' '-f' flag, available flows are: {', '.join(flows)}. During runtime, following commands can be used. {Commands.get_instructions()}."  # noqa: E501

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
    in_codeblock = False

    for line in lines:
        # Check for codeblock markers
        if line.strip().startswith("```"):
            in_codeblock = not in_codeblock
            # Skip the codeblock marker lines entirely
            continue

        # Apply markdown styling and remove markdown codes
        styled_line, clean_line = apply_markdown_styling(line, in_codeblock)

        if len(clean_line) <= MAX_WIDTH:
            wrapped_lines.append(styled_line)
        else:
            # For long lines, we need to wrap the clean text first, then style
            # Detect list items and their indentation on the clean text
            list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+", clean_line)
            if list_match:
                # Handle list items
                indent = list_match.group(1)  # Leading whitespace
                marker = list_match.group(2)  # List marker (-, *, +, or number.)
                # Calculate the hanging indent (indent + marker + space)
                hanging_indent = len(indent) + len(marker) + 1
                wrapped = textwrap.fill(
                    clean_line, width=MAX_WIDTH, initial_indent="", subsequent_indent=" " * hanging_indent
                )
            else:
                # Handle regular lines - preserve any leading whitespace
                leading_space_match = re.match(r"^(\s*)", clean_line)
                leading_space = leading_space_match.group(1) if leading_space_match else ""
                wrapped = textwrap.fill(clean_line, width=MAX_WIDTH, initial_indent="", subsequent_indent=leading_space)

            # Apply styling to the wrapped text
            styled_wrapped, _ = apply_markdown_styling(wrapped, in_codeblock)
            wrapped_lines.append(styled_wrapped)

    return "\n".join(wrapped_lines)


def apply_markdown_styling(text: str, in_codeblock: bool = False) -> tuple[str, str]:
    """Apply markdown styling to text and return (styled_text, clean_text)."""
    clean_text = text

    if in_codeblock:
        # Inside a codeblock - green text, no background
        return click.style(text, fg=(0, 0, 0)), clean_text

    # Handle inline code blocks first (single backticks)
    def style_inline_code(match):
        code_content = match.group(1)  # Content between backticks
        return click.style(code_content, fg=(0, 0, 0))

    def clean_inline_code(match):
        return match.group(1)  # Just return the content, remove backticks

    # Handle bold text (**text** or __text__)
    def style_bold(match):
        bold_content = match.group(1)  # Content between markers
        return click.style(bold_content, fg="cyan", bold=True)

    def clean_bold(match):
        return match.group(1)  # Just return the content, remove markers

    # Create clean text (remove markdown codes)
    clean_text = re.sub(r"`([^`]+)`", clean_inline_code, clean_text)
    clean_text = re.sub(r"\*\*([^*]+)\*\*", clean_bold, clean_text)
    clean_text = re.sub(r"__([^_]+)__", clean_bold, clean_text)

    # Create styled text (apply colors but remove markdown codes)
    styled_text = re.sub(r"`([^`]+)`", style_inline_code, text)
    styled_text = re.sub(r"\*\*([^*]+)\*\*", style_bold, styled_text)
    styled_text = re.sub(r"__([^_]+)__", style_bold, styled_text)

    return styled_text, clean_text
