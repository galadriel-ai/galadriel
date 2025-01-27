PRICES = {"CHEAP": 1, "EXP": 10}


# Not a tool but a function used from within a tool (at least for now)
def get_token_price(token: str) -> float:  # Return USDC
    return PRICES[token]
