import argparse

# TODO: redo the interface from argparse to click 
# https://click.palletsprojects.com/en/stable/

def create_parser_critic() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process a file with given instructions. -p / --path = relative or full path to a file."
    )
    # Add the -p --path argument
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        required=True,
        help="Relative path to the file",
    )
    # Add the -i --instruct argument
    parser.add_argument(
        "-i",
        "--instruct",
        type=str,
        required=False,
        default="",
        help="Additional instructions for the LLM",
    )
    return parser
