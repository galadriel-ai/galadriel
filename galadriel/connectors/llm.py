import asyncio
import os
from typing import Iterable
from typing import Optional

from openai import AsyncOpenAI
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from galadriel.logging_utils import get_agent_logger

logger = get_agent_logger()

RETRY_COUNT: int = 3


class LlmException(Exception):
    pass


class LlmClient:
    api_key: str

    def __init__(self, _base_url: Optional[str] = None, _api_key: Optional[str] = None):
        if _base_url:
            base_url = _base_url
        else:
            base_url = os.getenv("LLM_BASE_URL", "")
        if not base_url:
            logger.debug(
                "Missing LLM base_url, in constructor and/or LLM_BASE_URL environment variable, defaulting to OpenAI"
            )
            base_url = "https://api.openai.com/v1"
        if _api_key:
            api_key = _api_key
        else:
            api_key = os.getenv("LLM_API_KEY", "")
            if not api_key:
                raise LlmException("Missing LLM API key, in constructor and/or LLM_API_KEY environment variable")
        if not api_key:
            raise LlmException("Missing LLM base_url, in constructor and/or LLM_BASE_URL environment variable")
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        # Configurations?

    async def completion(self, model: str, messages: Iterable[ChatCompletionMessageParam]) -> Optional[ChatCompletion]:
        for i in range(RETRY_COUNT):
            try:
                return await self.client.chat.completions.create(model=model, messages=messages)
            except Exception as e:
                logger.error("Error calling Galadriel completions API", e)
            # Retry after 4 * i seconds
            await asyncio.sleep(int(min(60, 4**i)))
        return None
