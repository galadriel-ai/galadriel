import logging
import os
from typing import Optional

import discord
from discord.ext import commands

from galadriel import AgentInput
from galadriel import AgentOutput
from galadriel.entities import Message, Proof
from galadriel.entities import PushOnlyQueue


class DiscordClient(commands.Bot, AgentInput, AgentOutput):
    """A Discord bot client that can both receive and send messages.

    This class implements both AgentInput and AgentOutput interfaces to provide
    bidirectional communication between Discord and the agent system. It handles
    message reception, command processing, and response delivery.

    Attributes:
        message_queue: Queue for storing received messages
        guild_id: ID of the Discord server the bot is connected to
        logger: Logger instance for tracking bot activities
    """

    def __init__(self, guild_id: str, logger: Optional[logging.Logger] = None):
        """Initialize the Discord client.

        Args:
            guild_id (str): The ID of the Discord server to connect to
            logger (Optional[logging.Logger]): Custom logger instance. If None,
                                             creates a default logger
        """
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guild_messages = True

        super().__init__(command_prefix="!", intents=intents)
        self.message_queue: Optional[PushOnlyQueue] = None
        self.guild_id = guild_id
        self.logger = logger or logging.getLogger("discord_client")

    async def on_ready(self):
        """Event handler called when the bot successfully connects to Discord.

        Logs the bot's connected status and username.
        """
        self.logger.info(f"Bot connected as {self.user.name}")

    async def setup_hook(self):
        """Initialize the bot's commands and sync them with the Discord server.

        This method is called automatically during bot startup to register
        commands and establish the connection with the specified guild.

        Raises:
            discord.HTTPException: If command synchronization fails
        """

        # Sync with specific guild
        guild = discord.Object(id=int(self.guild_id))
        try:
            await self.tree.sync(guild=guild)
            self.logger.info(f"Connected to guild {self.guild_id}")
        except discord.HTTPException as e:
            self.logger.error(f"Failed to sync commands to guild {self.guild_id}: {e}")

    # pylint: disable=W0221
    async def on_message(self, message: discord.Message):
        """Event handler for processing incoming Discord messages.

        Converts Discord messages to Message objects and adds them to the
        message queue. Ignores messages sent by the bot itself.

        Args:
            message (discord.Message): The received Discord message

        Raises:
            Exception: If message queue processing fails
        """
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Create Message object and add to queue
        try:
            msg = Message(
                content=message.content,
                conversation_id=str(message.channel.id),
                additional_kwargs={
                    "author": message.author.name,
                    "message_id": message.id,
                    "timestamp": str(message.created_at.isoformat()),
                },
            )
            await self.message_queue.put(msg)  # type: ignore
            self.logger.info(f"Added message to queue: {msg}")
        except Exception as e:
            self.logger.error(f"Failed to add message to queue: {e}")
            raise e

    async def start(self, queue: PushOnlyQueue) -> None:  # type: ignore[override]
        """Start the Discord bot and connect it to the message queue.

        Args:
            queue (PushOnlyQueue): Queue for storing received messages

        Note:
            Requires DISCORD_TOKEN environment variable to be set
        """
        self.message_queue = queue
        await super().start(os.getenv("DISCORD_TOKEN", ""))

    async def send(self, request: Message, response: Message, proof: Optional[Proof] = None) -> None:
        """Send a response message to the appropriate Discord channel.

        Args:
            request (Message): The original request message (unused)
            response (Message): The response to send to Discord

        Raises:
            ValueError: If the response's conversation_id is None
            Exception: If message sending fails
        """
        try:
            if response.conversation_id is None:
                raise ValueError("conversation_id cannot be None")
            channel = self.get_channel(int(response.conversation_id))
            await channel.send(response.content)  # type: ignore[union-attr]
        except Exception as e:
            self.logger.error(f"Failed to post output: {e}")
            raise e
