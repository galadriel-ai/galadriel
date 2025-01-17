import asyncio
from typing import Optional, Dict
import os
from smolagents import Tool, ToolCallingAgent
from smolagents.agents import LogLevel
from typing import List, Callable
from rich.text import Text
from galadriel_agent.clients.discord_bot import DiscordClient
import json



class DiscordMultiStepAgent(ToolCallingAgent):
    def __init__(
        self,
        database: List[Dict[str, str]],
        character_prompt: str,
        character_name: str,
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
        self.database = database
        self.character_prompt = character_prompt
        self.character_name = character_name
        self.message_queue = asyncio.Queue()
        self.discord_client = DiscordClient(self.message_queue, guild_id=guild_id, logger=self.logger)
        self.discord_token = discord_token
        self.is_running = False
    

    async def _process_messages(self):
        """Separate task for processing messages from the queue"""
        while self.is_running:
            try:
                message = await self.message_queue.get()
                task_message = self.character_prompt.replace("{{message}}", message.content)\
                                                  .replace("{{user_name}}", message.author)\
                                                  .replace("{{memories}}", str(self.database))
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
                
                # Save message and response to database
                if not hasattr(self, 'database'):
                    self.database = []
                    
                conversation = {
                    message.author: message.content,
                    self.character_name: response_text
                }
                self.database.append(conversation)
                
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

    load_dotenv(dotenv_path=Path(".") / ".env", override=True)
    model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

    # very dummy database for now, it contains the past exchanged messages/memories
    database: List[Dict[str, str]] = []

    json_path = Path("galadriel_agent/agent_configuration/example_elon_musk.json")
    try:
        hydrated_character_prompt, character_name = load_agent_template(DISCORD_SYSTEM_PROMPT, json_path)
    except Exception as e:
        print(f"Error loading agent template: {e}")

    agent = DiscordMultiStepAgent(
        database=database,
        character_prompt=hydrated_character_prompt,
        character_name=character_name,
        tools=[get_weather, get_time],
        model=model,
        discord_token=os.getenv("DISCORD_TOKEN"),
        guild_id=os.getenv("DISCORD_GUILD_ID"),
        max_steps=6
    )
    asyncio.run(agent.run())