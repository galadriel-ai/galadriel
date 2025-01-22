from typing import Dict

# Client interface, client itself can be Twitter, Discord, CLI, API etc...
class Client:
    async def get_input(self) -> Dict:
        pass
    async def post_output(self, response: Dict, proof: str):
        pass