import asyncio
from datetime import datetime
from typing import Optional, Dict
import os
from uuid import uuid4
from smolagents import Tool, ToolCallingAgent
from smolagents.agents import LogLevel
from typing import List, Callable
from rich.text import Text
from galadriel_agent.clients.discord_bot import DiscordClient
import json

from galadriel_agent.clients.memory_repository import EmbeddingClient, MemoryRepository, Memory



class DiscordMultiStepAgent(ToolCallingAgent):
    def __init__(
        self,
        character_json_path: str,
        memory_repository: MemoryRepository,
        tools: List[Tool],
        model: Callable[[List[Dict[str, str]]], str],
        discord_token: str,
        guild_id: str,
        system_prompt: Optional[str] = None,
        tool_description_template: Optional[str] = None,
        max_steps: int = 6,
        tool_parser: Optional[Callable] = None,
        add_base_tools: bool = False,
        verbosity_level: int = 1,
        grammar: Optional[Dict[str, str]] = None,
        managed_agents: Optional[List] = None,
        step_callbacks: Optional[List[Callable]] = None,
        planning_interval: Optional[int] = None,
    ):
        super().__init__(
            tools=tools,
            model=model,
            system_prompt=system_prompt,
            tool_description_template=tool_description_template,
            max_steps=max_steps,
            tool_parser=tool_parser,
            add_base_tools=add_base_tools,
            verbosity_level=verbosity_level,
            grammar=grammar,
            managed_agents=managed_agents,
            step_callbacks=step_callbacks,
            planning_interval=planning_interval,
        )
        
        # Discord-specific initialization
        self.character_json_path = character_json_path
        try:
            self.character_prompt, self.character_name = load_agent_template(DISCORD_SYSTEM_PROMPT,
                                                                             Path(self.character_json_path))
        except Exception as e:
            print(f"Error loading agent json: {e}")
        try:
            self.embedding_client = EmbeddingClient(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            print(f"Error loading embedding client: {e}")
        try:
            self.memory_repository = memory_repository
        except Exception as e:
            print(f"Error loading memory repository: {e}")
        self.message_queue = asyncio.Queue()
        self.discord_client = DiscordClient(self.message_queue, guild_id=guild_id, logger=self.logger)
        self.discord_token = discord_token
        self.is_running = False
    

    async def _process_messages(self):
        """Separate task for processing messages from the queue"""
        while self.is_running:
            try:
                message = await self.message_queue.get()
                message_embedding = await self.embedding_client.embed_text(message.content)
                # todo: retrieve long term memory with similarity above threshold instead of only top_k
                long_term_memories = await self.memory_repository.query_long_term_memory(user_id=message.author,
                                                                                 conversation_id=message.channel_id,
                                                                                 embedding=message_embedding,
                                                                                 top_k=2)
                short_term_memories = await self.memory_repository.get_short_term_memory(user_id=message.author,
                                                                                 conversation_id=message.channel_id,
                                                                                 limit=10)
                task_message = self.character_prompt.replace("{{message}}", message.content)\
                                                  .replace("{{user_name}}", message.author)\
                                                  .replace("{{memories}}", "\n".join(str(memory) for memory in short_term_memories))\
                                                  .replace("{{long_term_memory}}", "\n".join(str(memory) for memory in long_term_memories))
                self.logger.log(Text(f"Task message: {task_message}"), level=LogLevel.INFO)   
                # Use parent's run method to process the message content
                response = super().run(
                    task=task_message,
                    stream=False,
                    reset=True,
                )
                
                # Extract message text if response is in JSON format
                response_text = str(response)
                try:
                    response_json = json.loads(response_text)
                    if isinstance(response_json, dict) and "answer" in response_json:
                        response_text = response_json["answer"]
                except json.JSONDecodeError:
                    pass  # Not JSON format, use original response
                   
                # Save memory
                try:
                    # embed user query and agent response into a single vector
                    content_embedding = await self.embedding_client.embed_text(message.content + " " + response_text)
                except Exception as e:
                    self.logger.log(Text(f"Error embedding conversation: {e}"), level=LogLevel.ERROR)
                    content_embedding = None
                try:
                    memory = Memory(
                        id=str(uuid4()),
                        message=message.content,
                        agent_response=response_text,
                        embedding=content_embedding,
                        author=message.author,
                        channel_id=message.channel_id,
                        agent_name=self.character_name,
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    await self.memory_repository.add_memory(user_id=message.author, memory=memory, conversation_id=message.channel_id)
                except Exception as e:
                    self.logger.log(Text(f"Error adding memory to repository: {e}"), level=LogLevel.ERROR)
                
                # Send response back to Discord
                channel = self.discord_client.get_channel(message.channel_id)
                if channel:
                    await channel.send(response_text)
                self.message_queue.task_done()
            except Exception as e:
                self.logger.log(Text(f"Error processing message: {e}"), level=LogLevel.ERROR)   
                continue  # Continue processing even if one message fails

    async def run(self):
        """
        Main loop that processes Discord messages from the queue.
        Overrides parent's run method to handle Discord-specific operation.
        """
        self.is_running = True
        
        try:
            # Create tasks for both the Discord client and message processing
            discord_task = asyncio.create_task(self.discord_client.start(self.discord_token))
            process_task = asyncio.create_task(self._process_messages())
            
            # Wait for both tasks to complete (or error)
            await asyncio.gather(discord_task, process_task)
                    
        except Exception as e:
            self.logger.log(Text(f"Error in Discord bot: {e}"), level=LogLevel.ERROR)
        finally:
            self.is_running = False
            await self.discord_client.close()



if __name__ == "__main__":
    from smolagents.models import LiteLLMModel
    from dotenv import load_dotenv
    from pathlib import Path
    from galadriel_agent.prompts.prompts import DISCORD_SYSTEM_PROMPT
    from galadriel_agent.prompts.format_prompt import load_agent_template
    from galadriel_agent.tools.example_tools import get_time, get_weather
    from galadriel_agent.clients.memory_repository import memory_repository

    load_dotenv(dotenv_path=Path(".") / ".env", override=True)
    model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

    agent = DiscordMultiStepAgent(
        memory_repository=memory_repository,
        character_json_path="galadriel_agent/agent_configuration/example_elon_musk.json",
        tools=[get_weather, get_time],
        model=model,
        discord_token=os.getenv("DISCORD_TOKEN"),
        guild_id=os.getenv("DISCORD_GUILD_ID"),
        max_steps=6
    )
    asyncio.run(agent.run())