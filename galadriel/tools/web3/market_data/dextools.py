"""DEXTools API tools for market data using the dextools-python library."""

from abc import ABC
from enum import Enum
import json
import os
import time
from typing import Optional

from dextools_python import DextoolsAPIV2

from galadriel.tools import Tool
from galadriel.logging_utils import get_agent_logger

logger = get_agent_logger()

# API configuration
DEXTOOLS_API_KEY = os.getenv("DEXTOOLS_API_KEY")


class DexToolsPlan(str, Enum):
    """DEXTools API plans."""

    FREE = "free"
    TRIAL = "trial"
    STANDARD = "standard"
    ADVANCED = "advanced"
    PRO = "pro"
    PARTNER = "partner"

    def __str__(self) -> str:
        return self.value


class DexToolsBase(Tool, ABC):
    """Base class for DEXTools API tools."""

    def __init__(self, plan: DexToolsPlan = DexToolsPlan.TRIAL):
        super().__init__()
        if not DEXTOOLS_API_KEY:
            raise ValueError("DEXTOOLS_API_KEY environment variable is not set")
        self.client = DextoolsAPIV2(DEXTOOLS_API_KEY, plan=str(plan))
        self.plan = plan


class GetBlockchainInfoTool(DexToolsBase):
    """Tool for fetching blockchain information from DEXTools."""

    name = "dextools_get_blockchain_info"
    description = "Retrieve name, website and DEXTools ID of a specific blockchain from DEXTools"
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier (e.g., 'ether', 'bsc', 'polygon')",
        }
    }
    output_type = "string"

    def forward(self, chain: str) -> str:
        """Fetch blockchain information.

        Args:
            chain: The blockchain identifier

        Returns:
            str: Blockchain information as JSON string
        """
        try:
            response = self.client.get_blockchain(chain)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch blockchain info: {e}")
            return json.dumps({"error": str(e)})


class GetBlockchainsTool(DexToolsBase):
    """Tool for fetching all blockchains from DEXTools."""

    name = "dextools_get_blockchains"
    description = "Get name, website and DEXTools ID for all supported blockchains from DEXTools"
    inputs = {
        "sort": {
            "type": "string",
            "description": "Sort field (e.g., 'name')",
            "nullable": True,
        },
        "order": {
            "type": "string",
            "description": "Sort order ('asc' or 'desc')",
            "nullable": True,
        },
        "page": {
            "type": "integer",
            "description": "Page number starting from 0, default is 0",
            "nullable": True,
        },
        "page_size": {
            "type": "integer",
            "description": "Number of blockchains to return, default is 20, max is 50",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> str:
        """Fetch all blockchains with optional sorting.

        Args:
            sort: Sort field
            order: Sort order ('asc' or 'desc')
            page: Page number starting from 0, default is 0
            page_size: Number of blockchains to return, default is 20, max is 50

        Returns:
            str: Blockchains information as JSON string
        """
        try:
            response = self.client.get_blockchains(
                sort=sort,
                order=order,
                page=page,
                pageSize=page_size,
            )
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch blockchains: {e}")
            return json.dumps({"error": str(e)})


class GetDexFactoryInfoTool(DexToolsBase):
    """Tool for fetching DEX factory information from DEXTools."""

    name = "dextools_get_dex_factory_info"
    description = "Retrieve information about a specific DEX factory from DEXTools, including factory address, name, website, number of pools, 24h volume, and number of swaps in last 24h"
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
        "factory_address": {
            "type": "string",
            "description": "The factory contract address",
        },
    }
    output_type = "string"

    def forward(self, chain: str, factory_address: str) -> str:
        """Fetch DEX factory information.

        Args:
            chain: The blockchain identifier
            factory_address: The factory contract address

        Returns:
            str: DEX factory information as JSON string
        """
        try:
            response = self.client.get_dex_factory_info(chain, factory_address)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch DEX factory info: {e}")
            return json.dumps({"error": str(e)})


class GetDexesTool(DexToolsBase):
    """Tool for fetching DEXes on a specific chain from DEXTools."""

    name = "dextools_get_dexes"
    description = "Get all supported DEXes on a specific chain from DEXTools, including DEX address, name, website, number of pools, 24h volume, and number of swaps in last 24h"
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
        "sort": {
            "type": "string",
            "description": "Sort field (e.g., 'name', 'creationBlock')",
            "nullable": True,
        },
        "order": {
            "type": "string",
            "description": "Sort order ('asc' or 'desc')",
            "nullable": True,
        },
        "page": {
            "type": "integer",
            "description": "Page number starting from 0, default is 0",
            "nullable": True,
        },
        "page_size": {
            "type": "integer",
            "description": "Number of DEXes to return, default is 20, max is 50",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        chain: str,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> str:
        """Fetch DEXes on a specific chain with optional sorting.

        Args:
            chain: The blockchain identifier
            sort: Sort field
            order: Sort order ('asc' or 'desc')
            page: Page number starting from 0, default is 0
            page_size: Number of DEXes to return, default is 20, max is 50

        Returns:
            str: DEXes information as JSON string
        """
        try:
            response = self.client.get_dexes(chain, sort=sort, order=order, page=page, pageSize=page_size)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch DEXes: {e}")
            return json.dumps({"error": str(e)})


class GetPoolInfoTool(DexToolsBase):
    """Tool for fetching pool information from DEXTools."""

    name = "dextools_get_pool_info"
    description = "Retrieve information about a specific pool from DEXTools, including creation time, exchange details (name and factory address), pool address, and information about both tokens in the pair (name, symbol, and address)"
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
        "pool_address": {
            "type": "string",
            "description": "The pool contract address",
        },
    }
    output_type = "string"

    def forward(self, chain: str, pool_address: str) -> str:
        """Fetch pool information.

        Args:
            chain: The blockchain identifier
            pool_address: The pool contract address

        Returns:
            str: Pool information as JSON string
        """
        try:
            response = self.client.get_pool(chain, pool_address)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch pool info: {e}")
            return json.dumps({"error": str(e)})


class GetPoolLiquidityTool(DexToolsBase):
    """Tool for fetching pool liquidity from DEXTools."""

    name = "dextools_get_pool_liquidity"
    description = "Retrieve liquidity information about a specific pool from DEXTools"
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
        "pool_address": {
            "type": "string",
            "description": "The pool contract address",
        },
    }
    output_type = "string"

    def forward(self, chain: str, pool_address: str) -> str:
        """Fetch pool liquidity.

        Args:
            chain: The blockchain identifier
            pool_address: The pool contract address

        Returns:
            str: Pool liquidity as JSON string
        """
        try:
            response = self.client.get_pool_liquidity(chain, pool_address)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch pool liquidity: {e}")
            return json.dumps({"error": str(e)})


class GetPoolsTool(DexToolsBase):
    """Tool for fetching pools from DEXTools."""

    name = "dextools_get_pools"
    description = "Retrieve pools from DEXTools with time range and optional sorting, including pool address, creation time, exchange details (name and factory address), and information about both tokens in the pair (name, symbol, and address)"
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
        "from_": {
            "type": "string",
            "description": "Start time (ISO format or block number)",
        },
        "to": {
            "type": "string",
            "description": "End time (ISO format or block number)",
        },
        "sort": {
            "type": "string",
            "description": "Sort field",
            "nullable": True,
        },
        "order": {
            "type": "string",
            "description": "Sort order ('asc' or 'desc')",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        chain: str,
        from_: str,
        to: str,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> str:
        """Fetch pools with time range and optional sorting.

        Args:
            chain: The blockchain identifier
            from_: Start time (ISO format or block number)
            to: End time (ISO format or block number)
            sort: Sort field
            order: Sort order ('asc' or 'desc')

        Returns:
            str: Pools as JSON string
        """
        try:
            response = self.client.get_pools(chain, from_=from_, to=to, sort=sort, order=order)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch pools: {e}")
            return json.dumps({"error": str(e)})


class GetTokenInfoTool(DexToolsBase):
    """Tool for fetching token information from DEXTools."""

    name = "dextools_get_token_info"
    description = "Retrieve detailed token information from DEXTools including name, symbol, logo, description, creation details, decimals and social media links"
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier (e.g. 'ether' for Ethereum)",
        },
        "token_address": {
            "type": "string",
            "description": "The token contract address to fetch information for",
        },
    }
    output_type = "string"

    def forward(self, chain: str, token_address: str) -> str:
        """Fetch token information.

        Args:
            chain: The blockchain identifier
            token_address: The token contract address

        Returns:
            str: Token information as JSON string
        """
        try:
            response = self.client.get_token_info(chain, token_address)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch token info: {e}")
            return json.dumps({"error": str(e)})


class GetTokenPriceTool(DexToolsBase):
    """Tool for fetching token price from DEXTools."""

    name = "dextools_get_token_price"
    description = "Retrieve token price information from DEXTools including current price, 24h price, and percentage variations over 5m, 1h, 6h and 24h periods in both token and chain native currency"
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
        "token_address": {
            "type": "string",
            "description": "The token contract address",
        },
    }
    output_type = "string"

    def forward(self, chain: str, token_address: str) -> str:
        """Fetch token price.

        Args:
            chain: The blockchain identifier
            token_address: The token contract address

        Returns:
            str: Token price as JSON string
        """
        try:
            response = self.client.get_token_price(chain, token_address)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch token price: {e}")
            return json.dumps({"error": str(e)})


class GetTokenPoolsTool(DexToolsBase):
    """Tool for fetching token pools from DEXTools."""

    name = "dextools_get_token_pools"
    description = "Retrieve token pools from DEXTools with time range and optional sorting"
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
        "token_address": {
            "type": "string",
            "description": "The token contract address",
        },
        "from_": {
            "type": "string",
            "description": "Start time (ISO format or block number)",
        },
        "to": {
            "type": "string",
            "description": "End time (ISO format or block number)",
        },
        "sort": {
            "type": "string",
            "description": "Sort field",
            "nullable": True,
        },
        "order": {
            "type": "string",
            "description": "Sort order ('asc' or 'desc')",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        chain: str,
        token_address: str,
        from_: str,
        to: str,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> str:
        """Fetch token pools with time range and optional sorting.

        Args:
            chain: The blockchain identifier
            token_address: The token contract address
            from_: Start time (ISO format or block number)
            to: End time (ISO format or block number)
            sort: Sort field
            order: Sort order ('asc' or 'desc')

        Returns:
            str: Token pools as JSON string
        """
        try:
            response = self.client.get_token_pools(
                chain,
                token_address,
                from_=from_,
                to=to,
                sort=sort,
                order=order,
            )
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch token pools: {e}")
            return json.dumps({"error": str(e)})


class GetRankingHotPoolsTool(DexToolsBase):
    """Tool for fetching hot pools ranking from DEXTools."""

    name = "dextools_get_ranking_hot_pools"
    description = "Retrieve hot pools ranking from DEXTools. Returns a list of the most active trading pools, including details like rank, creation time, exchange info, pool address, and token pair information."
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
    }
    output_type = "string"

    def forward(self, chain: str) -> str:
        """Fetch hot pools ranking.

        Args:
            chain: The blockchain identifier

        Returns:
            str: Hot pools ranking as JSON string
        """
        try:
            response = self.client.get_ranking_hotpools(chain)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch hot pools ranking: {e}")
            return json.dumps({"error": str(e)})


class GetRankingGainersTool(DexToolsBase):
    """Tool for fetching gainers ranking from DEXTools."""

    name = "dextools_get_ranking_gainers"
    description = "Retrieve a list of tokens that have gained the most in value. Returns an array of pools with exchange details, token pair info (addresses, symbols, names), creation time, fees, rank, current price, 24h price, and 24h variation percentage."

    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
    }
    output_type = "string"

    def forward(self, chain: str) -> str:
        """Fetch gainers ranking.

        Args:
            chain: The blockchain identifier

        Returns:
            str: Gainers ranking as JSON string
        """
        try:
            response = self.client.get_ranking_gainers(chain)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch gainers ranking: {e}")
            return json.dumps({"error": str(e)})


class GetRankingLosersTool(DexToolsBase):
    """Tool for fetching losers ranking from DEXTools."""

    name = "dextools_get_ranking_losers"
    description = "Retrieve a list of tokens that have lost the most in value. Returns an array of pools with exchange details, token pair info (addresses, symbols, names), creation time, fees, rank, current price, 24h price, and 24h variation percentage."
    inputs = {
        "chain": {
            "type": "string",
            "description": "The blockchain identifier",
        },
    }
    output_type = "string"

    def forward(self, chain: str) -> str:
        """Fetch losers ranking.

        Args:
            chain: The blockchain identifier

        Returns:
            str: Losers ranking as JSON string
        """
        try:
            response = self.client.get_ranking_losers(chain)
            return json.dumps(response, indent=2)
        except Exception as e:
            logger.error(f"Failed to fetch losers ranking: {e}")
            return json.dumps({"error": str(e)})


if __name__ == "__main__":
    try:
        # Test blockchain endpoints
        blockchain_tool = GetBlockchainInfoTool()
        blockchain_data = blockchain_tool.forward("ether")
        print("Blockchain Info:", blockchain_data)
        time.sleep(2)  # Sleep to respect rate limit

        blockchains_tool = GetBlockchainsTool()
        blockchains_data = blockchains_tool.forward(sort="name", order="desc")
        print("Blockchains:", blockchains_data)
        time.sleep(2)  # Sleep to respect rate limit

        # Test DEX endpoints
        dex_factory_tool = GetDexFactoryInfoTool()
        dex_factory_data = dex_factory_tool.forward("ether", "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")
        print("DEX Factory Info:", dex_factory_data)
        time.sleep(2)  # Sleep to respect rate limit

        dexes_tool = GetDexesTool()
        dexes_data = dexes_tool.forward("ether", sort="creationBlock", order="desc")
        print("DEXes:", dexes_data)
        time.sleep(2)  # Sleep to respect rate limit

        # Test pool endpoints
        pool_tool = GetPoolInfoTool()
        pool_data = pool_tool.forward("ether", "0xa29fe6ef9592b5d408cca961d0fb9b1faf497d6d")
        print("Pool Info:", pool_data)
        time.sleep(2)  # Sleep to respect rate limit

        pool_liquidity_tool = GetPoolLiquidityTool()
        pool_liquidity_data = pool_liquidity_tool.forward("ether", "0xa29fe6ef9592b5d408cca961d0fb9b1faf497d6d")
        print("Pool Liquidity:", pool_liquidity_data)
        time.sleep(2)  # Sleep to respect rate limit

        pools_tool = GetPoolsTool()
        pools_data = pools_tool.forward("ether", from_="18570000", to="18570500", sort="creationBlock", order="desc")
        print("Pools:", pools_data)
        time.sleep(2)  # Sleep to respect rate limit

        # Test token endpoints
        token_tool = GetTokenInfoTool()
        token_data = token_tool.forward("ether", "0xfb7b4564402e5500db5bb6d63ae671302777c75a")
        print("Token Info:", token_data)
        time.sleep(2)  # Sleep to respect rate limit

        token_price_tool = GetTokenPriceTool()
        token_price_data = token_price_tool.forward("ether", "0xfb7b4564402e5500db5bb6d63ae671302777c75a")
        print("Token Price:", token_price_data)
        time.sleep(2)  # Sleep to respect rate limit

        token_pools_tool = GetTokenPoolsTool()
        token_pools_data = token_pools_tool.forward(
            chain="ether",
            token_address="0xfb7b4564402e5500db5bb6d63ae671302777c75a",
            from_="18570000",
            to="18570500",
            sort="creationBlock",
            order="desc",
        )
        print("Token Pools:", token_pools_data)
        time.sleep(2)  # Sleep to respect rate limit

        # Test ranking endpoints
        hot_pools_tool = GetRankingHotPoolsTool()
        hot_pools_data = hot_pools_tool.forward("ether")
        print("Hot Pools:", hot_pools_data)
        time.sleep(2)  # Sleep to respect rate limit

        gainers_tool = GetRankingGainersTool()
        gainers_data = gainers_tool.forward("ether")
        print("Gainers:", gainers_data)
        time.sleep(2)  # Sleep to respect rate limit

        losers_tool = GetRankingLosersTool()
        losers_data = losers_tool.forward("ether")
        print("Losers:", losers_data)

    except ValueError as e:
        print(f"Error: {e}")
