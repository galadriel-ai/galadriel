from datetime import datetime

from galadriel.core_agent import tool


@tool
def get_time(location: str) -> str:
    """
    Get current time in the given location.
    Args:
        location: the location
    """
    return f"The time in {location} is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
