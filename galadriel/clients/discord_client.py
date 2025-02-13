import logging
import os
from typing import Optional

import discord
from discord.ext import commands

from galadriel import AgentInput
from galadriel import AgentOutput
from galadriel.entities import HumanMessage, Proof
from galadriel.entities import Message
from galadriel.entities import PushOnlyQueue


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping_command(self, ctx):
        """A simple ping command to test the bot"""
        await ctx.send("Pong! 🏓")

    @commands.command(name="hello")
    async def hello_command(self, ctx):
        """Greet the user"""
        await ctx.send(f"Hello {ctx.author.name}! 👋")


class DiscordClient(commands.Bot, AgentInput, AgentOutput):
    def __init__(self, guild_id: str, logger: Optional[logging.Logger] = None):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guild_messages = True

        super().__init__(command_prefix="!", intents=intents)
        self.message_queue: Optional[PushOnlyQueue] = None
        self.guild_id = guild_id
        self.logger = logger or logging.getLogger("discord_client")

    async def on_ready(self):
        self.logger.info(f"Bot connected as {self.user.name}")

    async def setup_hook(self):
        # Register commands
        await self.add_cog(CommandsCog(self))

        # Sync with specific guild
        guild = discord.Object(id=int(self.guild_id))
        try:
            await self.tree.sync(guild=guild)
            self.logger.info(f"Connected to guild {self.guild_id}")
        except discord.HTTPException as e:
            self.logger.error(f"Failed to sync commands to guild {self.guild_id}: {e}")

    # pylint: disable=W0221
    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Create Message object and add to queue
        try:
            msg = HumanMessage(
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
        self.message_queue = queue
        await super().start(os.getenv("DISCORD_TOKEN", ""))

    async def send(self, request: Message, response: Message, proof: Proof) -> None:
        try:
            if response.conversation_id is None:
                raise ValueError("conversation_id cannot be None")
            channel = self.get_channel(int(response.conversation_id))
            await channel.send(response.content)  # type: ignore[union-attr]
        except Exception as e:
            self.logger.error(f"Failed to post output: {e}")
            raise e
