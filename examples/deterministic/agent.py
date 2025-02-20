import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import Agent, AgentRuntime, LiteLLMModel
from galadriel.clients import Cron
from galadriel.clients.twitter_post_client import TwitterPostClient
from galadriel.entities import Message

load_dotenv(dotenv_path=Path(".") / ".env", override=True)
llm_model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

POST_INTERVAL_SECONDS = 3 * 60 * 60  # 3 hours
AGENT_PROMPT = """
You are a humorous Twitter user. Generate a short tweet (1-2 sentences). About any topic.
"""


class TwitterAgent(Agent):
    prompt: str
    model: LiteLLMModel

    def __init__(
        self,
        prompt: str,
        model: LiteLLMModel,
    ):
        self.prompt = prompt
        self.model = model

    async def execute(self, request: Message) -> Message:
        response = self.model(
            [
                {
                    "role": "system",
                    "content": self.prompt,
                }
            ]
        )
        return Message(content=response.content)


agent = TwitterAgent(
    prompt=AGENT_PROMPT,
    model=llm_model,
)

runtime = AgentRuntime(
    agent=agent,
    inputs=[Cron(POST_INTERVAL_SECONDS)],
    outputs=[TwitterPostClient()],
)

asyncio.run(runtime.run())
