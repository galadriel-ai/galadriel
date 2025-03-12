import json
import logging
import os
import asyncio
from typing import Any
from abc import ABC

from allora_sdk.v2.api_client import (
    AlloraAPIClient,
    ChainSlug,
    PriceInferenceToken,
    PriceInferenceTimeframe,
)

from galadriel.tools import Tool

logger = logging.getLogger(__name__)


class AlloraBaseTool(Tool, ABC):
    """Base class for Allora Network tools.

    This class provides common functionality for all Allora tools, including
    client initialization, API key validation, and request handling.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the Allora tool.

        Args:
            *args: Variable length argument list passed to parent Tool class
            **kwargs: Arbitrary keyword arguments passed to parent Tool class

        Raises:
            ValueError: If ALLORA_API_KEY environment variable is not set
        """
        self.api_key = os.getenv("ALLORA_API_KEY")
        if not self.api_key:
            raise ValueError("ALLORA_API_KEY environment variable is not set")

        self.chain_slug = os.getenv("ALLORA_CHAIN_SLUG", ChainSlug.TESTNET)
        self._client = None
        super().__init__(*args, **kwargs)

    def _get_client(self) -> AlloraAPIClient:
        """Get or create Allora client"""
        if not self._client:
            self._client = AlloraAPIClient(chain_slug=self.chain_slug, api_key=self.api_key)
        return self._client

    def _make_request(self, method_name: str, *args, **kwargs) -> Any:
        """Make API request with error handling"""
        try:
            client = self._get_client()
            method = getattr(client, method_name)

            # Create event loop for async calls
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(method(*args, **kwargs))
                return response
            finally:
                loop.close()

        except Exception as e:
            raise ValueError(f"API request failed: {str(e)}")


class AlloraListTopicsTool(AlloraBaseTool):
    """Tool for listing available Allora Network topics.

    Retrieves a list of all available topics from the Allora Network.
    """

    name = "allora_list_topics"
    description = "List all available Allora Network topics for market forecasting"
    inputs = {}  # type: ignore
    output_type = "string"

    def forward(self) -> str:  # pylint: disable=W0221
        """List all available Allora Network topics.

        Returns:
            str: JSON string containing all available topics
        """
        try:
            topics = self._make_request("get_all_topics")
            return json.dumps([topic.model_dump() for topic in topics])
        except Exception as e:
            logger.error(f"Failed to list topics: {str(e)}")
            return json.dumps({"error": str(e)})


class AlloraGetInferenceTool(AlloraBaseTool):
    """Tool for retrieving inference data from Allora Network.

    Fetches inference data for a specific topic from the Allora Network.
    """

    name = "allora_get_inference"
    description = "Get market forecasting inference from Allora Network for a specific topic"
    inputs = {"topic_id": {"type": "integer", "description": "The ID of the topic to get inference for"}}
    output_type = "string"

    def forward(self, topic_id: int) -> str:  # pylint: disable=W0221
        """Get inference from Allora Network for a specific topic.

        Args:
            topic_id (int): The ID of the topic to get inference for

        Returns:
            str: JSON string containing inference data
        """
        try:
            response = self._make_request("get_inference_by_topic_id", topic_id)
            return json.dumps(response.model_dump())
        except Exception as e:
            logger.error(f"Failed to get inference: {str(e)}")
            return json.dumps({"error": str(e)})


class AlloraGetPriceInferenceTool(AlloraBaseTool):
    """Tool for retrieving price inference data from Allora Network.

    Fetches price inference data for a specific cryptocurrency and timeframe.
    """

    name = "allora_get_price_inference"
    description = "Get price inference from Allora Network for a specific cryptocurrency and timeframe"
    inputs = {
        "token": {
            "type": "string",
            "description": "The cryptocurrency token (supported tokens: BTC, ETH)",
            "enum": [t.value for t in PriceInferenceToken],
        },
        "timeframe": {
            "type": "string",
            "description": "The timeframe for the price inference (supported timeframes: 5m, 8h)",
            "enum": [t.value for t in PriceInferenceTimeframe],
        },
    }
    output_type = "string"

    def forward(self, token: str, timeframe: str) -> str:  # pylint: disable=W0221
        """Get price inference from Allora Network for a specific cryptocurrency and timeframe.

        Args:
            token (str): The cryptocurrency token (supported tokens: BTC, ETH)
            timeframe (str): The timeframe for the price inference (supported timeframes: 5m, 8h)

        Returns:
            str: JSON string containing price inference data
        """
        try:
            # Convert string inputs to enum values
            token_enum = PriceInferenceToken(token)
            timeframe_enum = PriceInferenceTimeframe(timeframe)

            response = self._make_request("get_price_inference", token_enum, timeframe_enum)

            # Extract inference data
            inference_data = {
                "token": token,
                "timeframe": timeframe,
                "inference": response.inference_data.network_inference_normalized,
                "confidence_intervals": {
                    "percentiles": (response.inference_data.confidence_interval_percentiles_normalized),
                    "values": response.inference_data.confidence_interval_values_normalized,
                },
                "timestamp": response.inference_data.timestamp,
            }

            return json.dumps(inference_data)
        except Exception as e:
            logger.error(f"Failed to get price inference: {str(e)}")
            return json.dumps({"error": str(e)})


if __name__ == "__main__":
    os.environ["ALLORA_CHAIN_SLUG"] = "mainnet"
    allora_list_topics_tool = AlloraListTopicsTool()
    print(allora_list_topics_tool.forward())
    allora_get_inference_tool = AlloraGetInferenceTool()
    print(allora_get_inference_tool.forward(1))
    allora_get_price_inference_tool = AlloraGetPriceInferenceTool()
    print(allora_get_price_inference_tool.forward("BTC", "8h"))
