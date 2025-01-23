from smolagents import tool


@tool
def dex_screener_api(task: str) -> str:
    """
    Get the latest token profiles. Returns the results as a big chunk of text with
    the chain, token address and the description of the Token.
    Args:
         task: empty
    """
    import requests

    response = requests.get(
        "https://api.dexscreener.com/token-profiles/latest/v1",
        headers={},
    )
    data = response.json()
    result = ""
    for token in data:
        try:
            d = "Chain: " + token["chainId"]
            d += ", tokenAddress: " + token["tokenAddress"]
            d += ", description: " + token["description"]
            for link in token["links"]:
                d += f', {link["type"]}: {link["url"]}'
            result += d + "\n"
        except:
            pass
    return result
