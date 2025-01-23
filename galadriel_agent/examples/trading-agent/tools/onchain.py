import json
from typing import Dict

from smolagents import tool

from tools.price_feed import get_token_price

Portfolio = Dict[str, float]

# Dictionary to store user balances
user_portfolios: Dict[str, Portfolio] = {}

# This isn't a tool, but a helper function to update user balances
def deposit_usdc(user_address: str, amount: float) -> str:
    """
    Deposits USDC into the user's portfolio.

    Args:
        user_address: The address of the user.
        amount: The amount of USDC to deposit.

    Returns:
        A message indicating the result of the deposit.
    """
    if user_address not in user_portfolios:
        user_portfolios[user_address] = {}  # Initialize portfolio if user is new

    if "USDC" not in user_portfolios[user_address]:
        user_portfolios[user_address]["USDC"] = 0.0  # Initialize USDC balance if needed

    user_portfolios[user_address]["USDC"] += amount
    return f"Successfully deposited {amount} USDC into {user_address}'s account."


def deposit_token(user_address: str, token: str, amount: float) -> str:
    """
    Deposits tokens into the user's portfolio.

    Args:
        user_address: The address of the user.
        token: The token symbol (e.g., "SOL", "BTC").
        amount: The amount of tokens to deposit.

    Returns:
        A message indicating the result of the deposit.
    """
    if user_address not in user_portfolios:
        user_portfolios[user_address] = {}  # Initialize portfolio if user is new

    if token not in user_portfolios[user_address]:
        user_portfolios[user_address][token] = 0.0  # Initialize token balance if needed

    user_portfolios[user_address][token] += amount
    return f"Successfully deposited {amount} {token} into {user_address}'s account."


@tool
def swap_token(user_address: str, token1: str, token2: str, amount: float) -> str:
    """
    Swaps one token for another in the user's portfolio.

    Args:
        user_address: The address of the user.
        token1: The token to sell.
        token2: The token to buy.
        amount: The amount of token1 to swap.

    Returns:
        A message indicating the result of the swap.
    """
    if user_address not in user_portfolios:
        return "User does not have a portfolio."

    if token1 not in user_portfolios[user_address]:
        return f"User does not have any {token1} to swap."

    if user_portfolios[user_address][token1] < amount:
        return f"User does not have enough {token1} to swap."

    if token2 not in user_portfolios[user_address]:
        user_portfolios[user_address][token2] = 0.0  # Initialize token2 balance if needed

    user_portfolios[user_address][token1] -= amount
    user_portfolios[user_address][token2] += amount
    return f"Successfully swapped {amount} {token1} for {token2}."


def update_user_balance(user_address: str, token: str, amount: float) -> str:
    """
    Updates the user's token balance in the system.

    Args:
        user_address: The address of the user.
        token: The token symbol (e.g., "SOL", "BTC").
        amount: The amount to add (or subtract if negative) to the user's balance.

    Returns:
        A message indicating success or failure.
    """
    if user_address not in user_portfolios:
        user_portfolios[user_address] = {}  # Initialize portfolio if user is new

    if token not in user_portfolios[user_address]:
        user_portfolios[user_address][token] = 0.0  # Initialize token balance if needed

    user_portfolios[user_address][token] += amount
    return "User balance updated successfully."

@tool
def get_all_users() -> str:  # Return type is now str
    """
    Returns a JSON string containing a list of user addresses
    who have deposited funds.

    Returns:
        A JSON string with user addresses.
    """
    users = list(user_portfolios.keys())
    return json.dumps(users)


@tool
def get_all_portfolios(dummy: dict) -> str:
    """
    Returns a JSON string containing the portfolios of all users.

    Args:
        dummy: A dummy argument to match the required function signature.

    Returns:
        A JSON string with all user's portfolio.
    """
    return json.dumps(user_portfolios)


@tool
def get_user_balance(user_address: str, token: str) -> float:
    """
    Retrieves the user's balance for a specific token.

    Args:
        user_address: The address of the user.
        token: The token symbol.

    Returns:
        The user's balance for the specified token.
    """
    if user_address in user_portfolios:
        return user_portfolios[user_address].get(token, 0.0)  # Return 0 if token not found
    else:
        return 0.0

@tool
def place_buy_order(user_address: str, asset: str, quantity: float) -> str:
    """
    Places a buy order for the specified asset.

    Args:
        user_address: The address of the user placing the order.
        asset: The asset to buy (e.g., "BTC", "SOL").
        quantity: The quantity of the asset to buy.

    Returns:
        A message indicating the result of the order placement.
    """
    # In a real implementation, this would interact with an exchange API to place the order.
    # Here, we just check if the user has enough balance and simulate the order.

    order_cost = quantity * get_token_price(asset)
    available = get_user_balance(user_address, "USDC")

    if available < quantity * order_cost:
        return "Insufficient USDC balance to place buy order."

    update_user_balance(user_address, "USDC", -quantity * order_cost)
    update_user_balance(user_address, asset, quantity)
    return "Buy order placed successfully."


@tool
def calculate_slippage(asset: str, quantity: float) -> float:
    """
    Calculates the slippage for a given asset and quantity.

    Args:
        asset: The asset symbol (e.g., "BTC", "SOL").
        quantity: The quantity of the asset.

    Returns:
        The slippage percentage.
    """
    current_price = get_token_price(asset)
    # Assume a 1% slippage for demonstration purposes
    return current_price * 0.01 * quantity
