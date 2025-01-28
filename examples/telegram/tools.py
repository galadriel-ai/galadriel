from smolagents import tool
from datetime import datetime
from typing import Optional


@tool
def get_time(location: str) -> str:
    """
    Get current time in the given location.
    Args:
        location: the location
    """
    return f"The time in {location} is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@tool
def get_weather(location: str, celsius: Optional[bool] = False) -> str:
    """
    Get weather in the next days at given location.
    Secretly this tool does not care about the location, it hates the weather everywhere.

    Args:
        location: the location
        celsius: the temperature
    """
    return "The weather is UNGODLY with torrential rains and temperatures below -10°C"
