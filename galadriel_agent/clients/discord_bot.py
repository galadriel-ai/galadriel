import discord
from discord.ext import commands
import asyncio
from dataclasses import dataclass
from smolagents.agents import AgentLogger, LogLevel
from rich.text import Text


@dataclass
class Message:
    """Data class to store message information"""
    content: str
    channel_id: int
    author: str
    message_id: int

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

class DiscordClient(commands.Bot):
    def __init__(self, message_queue: asyncio.Queue, guild_id: str, logger: AgentLogger):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guild_messages = True
        
        super().__init__(command_prefix='!', intents=intents)
        self.message_queue = message_queue
        self.guild_id = guild_id
        self.logger = logger
    async def on_ready(self):
        self.logger.log(Text(f"Bot connected as {self.user.name}"), level=LogLevel.INFO)  
    
    async def setup_hook(self):
        # Register commands
        await self.add_cog(CommandsCog(self))
        
        # Sync with specific guild
        guild = discord.Object(id=int(self.guild_id))
        try:
            await self.tree.sync(guild=guild)
            self.logger.log(Text(f"Connected to guild {self.guild_id}"), level=LogLevel.INFO)
        except discord.HTTPException as e:
            self.logger.log(Text(f"Failed to sync commands to guild {self.guild_id}: {e}"), level=LogLevel.ERROR)
        
    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
            
        # Create Message object and add to queue
        msg = Message(
            content=message.content,
            channel_id=message.channel.id,
            author=message.author.name,
            message_id=message.id
        )
        await self.message_queue.put(msg)
        self.logger.log(Text(f"Added message to queue: {msg}"), level=LogLevel.INFO)