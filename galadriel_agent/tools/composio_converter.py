from galadriel_agent.core_agent import Tool
from composio_langchain import ComposioToolSet, App


def convert_action(api_key: str, action: str) -> Tool:
    composio_toolset = ComposioToolSet(api_key=api_key)
    return Tool.from_langchain(composio_toolset.get_tools(actions=[action])[0])


def convert_app(api_key: str, app: App) -> list[Tool]:
    composio_toolset = ComposioToolSet(api_key=api_key)
    return [
        Tool.from_langchain(tool) for tool in composio_toolset.get_tools(apps=[app])
    ]
