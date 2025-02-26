"""Cookie.fun API tools for market data."""

from abc import ABC
import json
import logging
import os
from typing import Dict, List, Optional

import requests

from galadriel.tools import Tool
from galadriel.logging_utils import get_agent_logger

logger = get_agent_logger()

# API Base URLs and configuration
COOKIE_FUN_API_BASE = "https://api.cookie.fun/v2"
COOKIE_FUN_API_KEY = os.getenv("COOKIE_FUN_API_KEY")


# Time intervals supported by the API
class TimeInterval:
    """Time intervals for Cookie.fun API."""

    THREE_DAYS = "_3Days"
    SEVEN_DAYS = "_7Days"


class ChainId:
    """Chain identifiers for different blockchains."""

    SOLANA = -2  # Special identifier for Solana
    ETHEREUM = 1
    BSC = 56
    ARBITRUM = 42161
    # Add more chains as needed


class CookieFunBase(Tool, ABC):
    """Base class for Cookie.fun API tools."""

    def __init__(self):
        super().__init__()
        if not COOKIE_FUN_API_KEY:
            raise ValueError("COOKIE_FUN_API_KEY environment variable is not set")
        self.headers = {"x-api-key": COOKIE_FUN_API_KEY}


class GetAgentByTwitterTool(CookieFunBase):
    """Tool for fetching agent data by Twitter username."""

    name = "get_agent_by_twitter"
    description = "Get agent data by Twitter username from Cookie.fun"
    inputs = {
        "twitter_username": {
            "type": "string",
            "description": "Twitter username of the agent",
        },
        "interval": {
            "type": "string",
            "description": "Time interval (_3Days, _7Days)",
            "default": "_7Days",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, twitter_username: str, interval: str = TimeInterval.SEVEN_DAYS) -> str:
        """Fetch agent data by Twitter username.

        Args:
            twitter_username (str): Twitter username of the agent
            interval (str, optional): Time interval. Defaults to "_7Days".

        Returns:
            str: Agent data including trading history and performance as JSON string
                Chain property in response indicates:
                - -2: Solana blockchain
                - Other numbers: EVM chain IDs (see chainlist.org)
        """
        try:
            response = requests.get(
                f"{COOKIE_FUN_API_BASE}/agents/twitterUsername/{twitter_username}",
                params={"interval": interval},
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch agent by Twitter username: {e}")
            return json.dumps({"error": str(e)})


class GetAgentByAddressTool(CookieFunBase):
    """Tool for fetching agent data by contract address."""

    name = "get_agent_by_address"
    description = "Get agent data by contract address from Cookie.fun"
    inputs = {
        "contract_address": {
            "type": "string",
            "description": "Contract address of the agent",
        },
        "interval": {
            "type": "string",
            "description": "Time interval (_3Days, _7Days)",
            "default": "_7Days",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, contract_address: str, interval: str = TimeInterval.SEVEN_DAYS) -> str:
        """Fetch agent data by contract address.

        Args:
            contract_address (str): Contract address of the agent
            interval (str, optional): Time interval. Defaults to "_7Days".

        Returns:
            str: Agent data including trading history and performance as JSON string
                Chain property in response indicates:
                - -2: Solana blockchain
                - Other numbers: EVM chain IDs (see chainlist.org)
        """
        try:
            response = requests.get(
                f"{COOKIE_FUN_API_BASE}/agents/contractAddress/{contract_address}",
                params={"interval": interval},
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch agent by contract address: {e}")
            return json.dumps({"error": str(e)})


class GetAgentsPagedTool(CookieFunBase):
    """Tool for fetching paginated list of agents ordered by mindshare."""

    name = "get_agents_paged"
    description = "Get list of agents details ordered by mindshare (descending)"
    inputs = {
        "interval": {
            "type": "string",
            "description": "Time interval (_3Days, _7Days)",
            "default": "_7Days",
            "nullable": True,
        },
        "page": {
            "type": "integer",
            "description": "Page number (starts at 1)",
            "default": 1,
            "nullable": True,
        },
        "page_size": {
            "type": "integer",
            "description": "Number of agents per page (1-25)",
            "default": 10,
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self, interval: str = TimeInterval.SEVEN_DAYS, page: int = 1, page_size: int = 10
    ) -> str:
        """Fetch paginated list of agents ordered by mindshare.

        Args:
            interval (str, optional): Time interval. Defaults to "_7Days".
            page (int, optional): Page number (starts at 1). Defaults to 1.
            page_size (int, optional): Number of agents per page (1-25). Defaults to 10.

        Returns:
            str: List of agents with their details as JSON string.
                Chain property in response indicates:
                - -2: Solana blockchain
                - Other numbers: EVM chain IDs (see chainlist.org)
        """
        try:
            # Validate page_size
            if not 1 <= page_size <= 25:
                raise ValueError("page_size must be between 1 and 25")

            # Validate page number
            if page < 1:
                raise ValueError("page must be greater than 0")

            response = requests.get(
                f"{COOKIE_FUN_API_BASE}/agents/agentsPaged",
                params={"interval": interval, "page": page, "pageSize": page_size},
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch agents list: {e}")
            return json.dumps({"error": str(e)})


if __name__ == "__main__":
    try:
        # Test agent endpoints
        twitter_tool = GetAgentByTwitterTool()
        twitter_data = twitter_tool.forward("cookiedotfun", TimeInterval.SEVEN_DAYS)
        print("Twitter Agent Data:", twitter_data)

        address_tool = GetAgentByAddressTool()
        address_data = address_tool.forward(
            "0xc0041ef357b183448b235a8ea73ce4e4ec8c265f", TimeInterval.THREE_DAYS
        )
        print("Address Agent Data:", address_data)

        # Test paginated agents list
        agents_tool = GetAgentsPagedTool()
        agents_data = agents_tool.forward(interval=TimeInterval.SEVEN_DAYS, page=1, page_size=2)
        print("Agents List:", agents_data)

    except ValueError as e:
        print(f"Error: {e}")
