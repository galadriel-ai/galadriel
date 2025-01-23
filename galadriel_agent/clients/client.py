import asyncio
from typing import Dict

# Client interface, client itself can be Twitter, Discord, CLI, API etc...
class Client:
    async def start(self, queue: asyncio.Queue) -> Dict:
        pass
    async def post_output(self, request, response: Dict, proof: str):
        pass