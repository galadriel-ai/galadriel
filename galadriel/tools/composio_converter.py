from composio_langchain import App
from composio_langchain import ComposioToolSet

from galadriel.tools import Tool


def convert_action(api_key: str, action: str) -> Tool:
    """
    Convert a single Composio action into a Galadriel Tool.

    This allows importing individual actions from Composio, like 'WEATHERMAP_WEATHER',
    rather than importing an entire app's worth of tools.

    Args:
        api_key (str): Composio API key
        action (str): Name of the Composio action to convert

    Returns:
        Tool: The converted Galadriel Tool
    """
    composio_toolset = ComposioToolSet(api_key=api_key)
    return Tool.from_langchain(composio_toolset.get_tools(actions=[action])[0])


def convert_app(api_key: str, app: App) -> list[Tool]:
    """
    Convert all tools from a Composio App into Galadriel Tools.

    Composio organizes related tools into Apps (e.g. GitHub, Weather).
    This converts all tools within a specified app into Galadriel Tools.

    Args:
        api_key (str): Composio API key
        app (App): The Composio App to convert

    Returns:
        list[Tool]: List of converted Galadriel Tools
    """
    composio_toolset = ComposioToolSet(api_key=api_key)
    return [Tool.from_langchain(tool) for tool in composio_toolset.get_tools(apps=[app])]
