import json
from galadriel.tools import tool


@tool
def fetch_mock_market_data() -> str:  # pylint: disable=W0613
    """
    Fetches market data for the Solana Devnet.

    Args:

    Returns:
        A JSON string containing market data for the Solana Devnet.
    """
    mock_market_data = json.dumps(
        [
            {
                "chainId": "solana",
                "dexId": "raydium",
                "pairAddress": "ftNSdLt7wuF9kKz6BxiUVWYWeRYGyt1RgL5sSjCVnJ2",
                "baseToken": {
                    "address": "ELJKW7qz3DA93K919agEk398kgeY1eGvs2u3GAfV3FLn",
                    "name": "DAIGE DEVNET",
                    "symbol": "DAIGE",
                },
                "quoteToken": {
                    "address": "So11111111111111111111111111111111111111112",
                    "name": "Wrapped SOL",
                    "symbol": "SOL",
                },
                "priceNative": "0.00000007161",
                "priceUsd": "0.00001362",
                "txns": {
                    "m5": {"buys": 0, "sells": 1},
                    "h1": {"buys": 13, "sells": 25},
                    "h6": {"buys": 64, "sells": 126},
                    "h24": {"buys": 11057, "sells": 4767},
                },
                "volume": {"h24": 946578.57, "h6": 8416.05, "h1": 2250.36, "m5": 0},
                "priceChange": {"m5": -0.1, "h1": -30.85, "h6": -29.27, "h24": -87.54},
                "liquidity": {"usd": 13537.61, "base": 496103405, "quote": 35.6157},
                "fdv": 13627,
                "marketCap": 13627,
                "pairCreatedAt": 1739310341000,
                "boosts": {"active": 5000},
            }
        ],
        indent=4,
    )
    return mock_market_data
