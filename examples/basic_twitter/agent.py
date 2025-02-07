import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import Agent
from galadriel import AgentOutput
from galadriel import AgentRuntime
from galadriel.clients import Cron
from galadriel.clients.twitter_post_client import TwitterPostClient
from galadriel.core_agent import LiteLLMModel
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
        response = self.model([
            {
                "role": "system",
                "content": self.prompt,
            }
        ])
        return Message(content=response.content)


class RandomOutput(AgentOutput):

    async def send(self, request: Message, response: Message) -> None:
        print(response)


agent = TwitterAgent(
    prompt=AGENT_PROMPT,
    model=llm_model,
    # TwitterCredentials(
    #         consumer_api_key=os.getenv("TWITTER_CONSUMER_API_KEY", ""),
    #         consumer_api_secret=os.getenv("TWITTER_CONSUMER_API_SECRET", ""),
    #         access_token=os.getenv("TWITTER_ACCESS_TOKEN", ""),
    #         access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET", ""),
    #     )
)

runtime = AgentRuntime(
    agent=agent,
    inputs=[Cron(POST_INTERVAL_SECONDS)],
    outputs=[TwitterPostClient()],
)

asyncio.run(runtime.run())
