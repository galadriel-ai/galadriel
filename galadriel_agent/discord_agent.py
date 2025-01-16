import asyncio
from typing import Optional, Dict
import os
from smolagents import MultiStepAgent, Tool, CodeAgent, ToolCallingAgent
from smolagents.agents import LogLevel, ActionStep, YELLOW_HEX, ToolCall
from typing import List, Callable, Union, Any
from rich.text import Text
from rich.panel import Panel
from smolagents.utils import AgentGenerationError
from smolagents.types import AgentImage, AgentAudio
from galadriel_agent.clients.discord_bot import DiscordClient




class DiscordMultiStepAgent(ToolCallingAgent):
    def __init__(
        self,
        character_prompt: str,
        character_system: str,
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
        self.character_prompt = character_prompt
        self.character_system = character_system
        self.message_queue = asyncio.Queue()
        self.discord_client = DiscordClient(self.message_queue, guild_id=guild_id, logger=self.logger)
        self.discord_token = discord_token
        self.is_running = False

    def step(self, log_entry: ActionStep) -> Union[None, Any]:
        """
        Perform one step in the ReAct framework: the agent thinks, acts, and observes the result.
        Returns None if the step is not final.
        """
        agent_memory = self.write_inner_memory_from_logs()

        self.input_messages = agent_memory

        # Add new step in logs
        log_entry.agent_memory = agent_memory.copy()

        try:
            model_message = self.model(
                self.input_messages,
                tools_to_call_from=list(self.tools.values()),
                stop_sequences=["Observation:"],
            )
            tool_call = model_message.tool_calls[0]
            tool_name, tool_call_id = tool_call.function.name, tool_call.id
            tool_arguments = tool_call.function.arguments

        except Exception as e:
            raise AgentGenerationError(
                f"Error in generating tool call with model:\n{e}"
            )

        log_entry.tool_calls = [
            ToolCall(name=tool_name, arguments=tool_arguments, id=tool_call_id)
        ]

        # Execute
        self.logger.log(
            Panel(
                Text(f"Calling tool: '{tool_name}' with arguments: {tool_arguments}")
            ),
            level=LogLevel.INFO,
        )
        if tool_name == "final_answer":
            if isinstance(tool_arguments, dict):
                if "answer" in tool_arguments:
                    answer = tool_arguments["answer"]
                else:
                    answer = tool_arguments
            else:
                answer = tool_arguments
            if (
                isinstance(answer, str) and answer in self.state.keys()
            ):  # if the answer is a state variable, return the value
                final_answer = self.state[answer]
                self.logger.log(
                    f"[bold {YELLOW_HEX}]Final answer:[/bold {YELLOW_HEX}] Extracting key '{answer}' from state to return value '{final_answer}'.",
                    level=LogLevel.INFO,
                )
            else:
                final_answer = answer
                self.logger.log(
                    Text(f"Final answer: {final_answer}", style=f"bold {YELLOW_HEX}"),
                    level=LogLevel.INFO,
                )

            # convert final answer to character's own voice
            try:
                message = self.character_prompt.replace("{{message}}", str(final_answer))
                self.logger.log(
                    Text(f"Character prompt: {message}", style=f"bold {YELLOW_HEX}"),
                    level=LogLevel.DEBUG,
                )
                character_prompt = [
                            {
                                "role": "system",
                                "content": self.character_system,
                            },
                            {
                                "role": "user",
                                "content": message,
                            }
                        ]
                final_answer = self.model(character_prompt).content

            except Exception as e:
                raise AgentGenerationError(
                    f"Error in generating tool call with model:\n{e}"
                )

            log_entry.action_output = final_answer
            return final_answer
        else:
            if tool_arguments is None:
                tool_arguments = {}
            observation = self.execute_tool_call(tool_name, tool_arguments)
            observation_type = type(observation)
            if observation_type in [AgentImage, AgentAudio]:
                if observation_type == AgentImage:
                    observation_name = "image.png"
                elif observation_type == AgentAudio:
                    observation_name = "audio.mp3"
                # TODO: observation naming could allow for different names of same type

                self.state[observation_name] = observation
                updated_information = f"Stored '{observation_name}' in memory."
            else:
                updated_information = str(observation).strip()
            self.logger.log(
                f"Observations: {updated_information.replace('[', '|')}",  # escape potential rich-tag-like components
                level=LogLevel.INFO,
            )
            log_entry.observations = updated_information
            return None
    
    async def _process_messages(self):
        """Separate task for processing messages from the queue"""
        while self.is_running:
            try:
                message = await self.message_queue.get()
                task = message.content #self.system_prompt.replace("{{message}}", message.content)
                print(task)
                # Use parent's run method to process the message content
                response = super().run(
                    task=task,
                    stream=False,
                    reset=True,
                )
                
                # Send response back to Discord
                channel = self.discord_client.get_channel(message.channel_id)
                if channel:
                    await channel.send(str(response))
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

    json_path = Path("galadriel_agent/agent_configuration/example_elon_musk.json")
    try:
        updated_template, character_system = load_agent_template(DISCORD_SYSTEM_PROMPT, json_path)
    except Exception as e:
        print(f"Error loading agent template: {e}")

    agent = DiscordMultiStepAgent(
        character_system=character_system,
        character_prompt=updated_template,
        tools=[get_weather, get_time],
        model=model,
        discord_token=os.getenv("DISCORD_TOKEN"),
        guild_id=os.getenv("DISCORD_GUILD_ID"),
        max_steps=6
    )
    asyncio.run(agent.run())