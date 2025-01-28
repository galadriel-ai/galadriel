import json
import os
from datetime import datetime
from pathlib import Path

from typing import List, Callable
from typing import Optional, Dict

from uuid import uuid4

from rich.text import Text
from smolagents import Tool
from smolagents import ToolCallingAgent
from smolagents.agents import LogLevel

from examples.telegram.prompts import TELEGRAM_SYSTEM_PROMPT
from galadriel_agent.agent import UserAgent

from galadriel_agent.clients.memory_repository import EmbeddingClient, MemoryRepository

from galadriel_agent.entities import Message, AgentMessage
from galadriel_agent.prompts.format_prompt import load_agent_template


class TelegramAgent(ToolCallingAgent, UserAgent):
    def __init__(
        self,
        character_json_path: str,
        memory_repository: MemoryRepository,
        tools: List[Tool],
        model: Callable[[List[Dict[str, str]]], str],
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

        self.character_json_path = character_json_path
        try:
            self.character_prompt, self.character_name = load_agent_template(
                TELEGRAM_SYSTEM_PROMPT, Path(self.character_json_path)
            )
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
        self.is_running = False

    async def run(self, message: Message) -> Message:
        try:
            message_embedding = await self.embedding_client.embed_text(message.content)
            # todo: retrieve long term memory with similarity above threshold instead of only top_k
            long_term_memories = await self.memory_repository.query_long_term_memory(
                user_id=message.additional_kwargs["author"],
                conversation_id=message.conversation_id,
                embedding=message_embedding,
                top_k=2,
            )
            short_term_memories = await self.memory_repository.get_short_term_memory(
                user_id=message.additional_kwargs["author"],
                conversation_id=message.conversation_id,
                limit=10,
            )
            task_message = (
                self.character_prompt.replace("{{message}}", message.content)
                .replace("{{user_name}}", message.additional_kwargs["author"])
                .replace(
                    "{{memories}}",
                    "\n".join(memory for memory in short_term_memories),
                )
                .replace(
                    "{{long_term_memory}}",
                    "\n".join(memory for memory in long_term_memories),
                )
            )
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
                content_embedding = await self.embedding_client.embed_text(
                    message.content + " " + response_text
                )
            except Exception as e:
                self.logger.log(
                    Text(f"Error embedding conversation: {e}"), level=LogLevel.ERROR
                )
                content_embedding = None
            try:
                memory = Message(
                    content=message.content,
                    conversation_id=message.conversation_id,
                    type="memory",
                    additional_kwargs={
                        "embeddings": content_embedding,
                        "agent_name": self.character_name,
                        "timestamp": message.additional_kwargs["timestamp"],
                        "author": message.additional_kwargs["author"],
                        "message_id": message.additional_kwargs["message_id"],
                        "agent_response": response_text,
                    },
                )
                await self.memory_repository.add_memory(memory=memory)
            except Exception as e:
                self.logger.log(
                    Text(f"Error adding memory to repository: {e}"),
                    level=LogLevel.ERROR,
                )
            return AgentMessage(
                content=response_text,
                conversation_id=message.conversation_id,
            )
        except Exception as e:
            self.logger.log(
                Text(f"Error processing message: {e}"), level=LogLevel.ERROR
            )
            return None
