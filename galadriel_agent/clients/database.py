import json
import os
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import aiofiles

from galadriel_agent.logging_utils import get_agent_logger
from galadriel_agent.models import Memory
from galadriel_agent.clients.s3 import S3Client
logger = get_agent_logger()

MEMORIES_FILE = "memories.json"


class DatabaseClient:
    memories_file_path: str

    def __init__(
        self,
        s3_client: S3Client,
        data_dir: str = "data",
    ):
        os.makedirs(data_dir, exist_ok=True)
        self.memories_file_path = os.path.join(data_dir, MEMORIES_FILE)

        if not os.path.exists(self.memories_file_path):
            with open(self.memories_file_path, "w", encoding="utf-8") as f:
                f.write(json.dumps([]))
        self.s3_client = s3_client

    async def _get_memories(self) -> List[Memory]:
        try:
            content = await _read_json_list(self.memories_file_path)
            return [Memory.from_dict(c) for c in content]
        except Exception:
            return []

    async def get_tweets(self) -> List[Memory]:
        try:
            memories = await self._get_memories()
            return [m for m in memories if m.type == "tweet"]
        except Exception:
            logger.error("Failed to get tweets", exc_info=True)
            return []

    async def get_latest_tweet(self) -> Optional[Memory]:
        tweets = await self.get_tweets()
        if not tweets:
            return None
        return tweets[-1]

    async def add_memory(self, memory: Memory) -> None:
        try:
            memories = await self._get_memories()
            memories.append(memory)
            memories_dict = [m.to_dict() for m in memories]
            await _write_json(self.memories_file_path, memories_dict)
        except Exception:
            logger.error("Failed to get memories", exc_info=True)
            return None
    
    async def upload_memories(self, agent_name: str) -> None:
        status = await self.s3_client.upload_file(self.memories_file_path, agent_name)
        if status:
            logger.info("Successfully uploaded memories to S3")
        else:
            logger.error("Failed to upload memories to S3")



async def _read_json_list(file_path: str) -> List[Dict]:
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        content = await f.read()
        return json.loads(content)


async def _write_json(file_path: str, content: Union[List, Dict]) -> None:
    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(content, indent=4))
