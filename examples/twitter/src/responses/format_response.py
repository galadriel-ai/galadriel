import re
from typing import Optional


def execute(response: str) -> Optional[str]:
    """
    Formats potential LLM response, returns None if response is not OK
    :param response: LLM response
    :return: Formatted LLM response if it can be formatted, None if invalid
    """
    if not response:
        return None
    url_pattern = r"\b(?:https?://)?(?:www\.)?[\w-]+(?:\.[\w-]+)+[\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-]"
    urls = re.findall(url_pattern, response)
    if urls:
        return None
    return response
