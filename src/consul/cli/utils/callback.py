from langchain.messages import AIMessage

from consul.cli.utils.text import get_terminal_handler


def interface_callback(*args: tuple, **kwargs: dict) -> None:  # noqa: ARG001
    """
    Function used as a callback from tool loop (react) flow.
    Updates spinner text, when tool is called and prints AI message if that message also contains a tool call.
    """
    # Try to retrieve state and do nothing if we don't manage to retrieve state
    state = kwargs.get("state")
    if not state:
        return

    # retrieve latest message and stop if the latest message is not from AI
    lmsg = state.get("messages", [])[-1]
    if not isinstance(lmsg, AIMessage):
        return

    io = get_terminal_handler()

    # If the AI wrote something and also called tools. print it
    calls = lmsg.tool_calls
    if calls and lmsg.content:
        io.display_message(f"Assistant:{lmsg.content}", format_markdown=True)

    # If calls are present, show the updated spinner message
    if calls:
        msg = f"Consulting {', '.join([f"'{c.get('name')}'" for c in calls])} tool(s)"
        io.restart_spinner(msg)
