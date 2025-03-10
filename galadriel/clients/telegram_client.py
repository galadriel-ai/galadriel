import logging
from datetime import datetime
from typing import Optional

from telebot import types
from telebot.async_telebot import AsyncTeleBot

from galadriel import AgentInput
from galadriel import AgentOutput
from galadriel.entities import Message, Proof
from galadriel.entities import PushOnlyQueue


class TelegramClient(AgentInput, AgentOutput):
    """A Telegram bot client that handles bidirectional message communication.

    This class implements both AgentInput and AgentOutput interfaces to provide
    integration with the Telegram messaging platform. It handles incoming messages
    from Telegram users and sends agent responses back to the appropriate chats.

    Attributes:
        token (str): The Telegram bot API token
        bot (AsyncTeleBot): The async Telegram bot instance
        queue (Optional[PushOnlyQueue]): Queue for storing incoming messages
        logger (logging.Logger): Logger instance for tracking bot activities
    """

    def __init__(self, token: str, logger: logging.Logger):
        """Initialize the Telegram client.

        Args:
            token (str): The Telegram bot API token for authentication
            logger (logging.Logger): Logger instance for tracking bot activities
        """
        self.token = token
        self.bot = AsyncTeleBot(token)
        self.queue: Optional[PushOnlyQueue] = None
        self.logger = logger

    async def start(self, queue: PushOnlyQueue) -> None:
        """Start the Telegram bot and begin processing messages.

        Sets up message handling and starts the bot's polling loop to receive
        messages from Telegram.

        Args:
            queue (PushOnlyQueue): Queue for storing incoming messages

        Note:
            This method runs indefinitely until the bot is stopped.
        """
        self.queue = queue

        @self.bot.message_handler(func=lambda message: True)
        async def handle_incoming_message(message: types.Message):
            """Process incoming Telegram messages.

            Converts Telegram messages to Message objects and adds them
            to the processing queue.

            Args:
                message (types.Message): The incoming Telegram message

            Note:
                The author name is constructed from the user's first_name and last_name
                if available, falling back to username or user ID if not.
            """
            if not self.queue:
                self.logger.warning("Queue not initialized. Ignoring incoming message.")
                return

            user = message.from_user
            # Construct author name from available user information
            author = f"{user.first_name} {user.last_name}".strip() if user.first_name else user.username or str(user.id)

            incoming = Message(
                content=message.text,
                conversation_id=str(message.chat.id),
                additional_kwargs={
                    "author": author,
                    "message_id": message.id,
                    "timestamp": str(datetime.now().isoformat()),
                },
            )
            await self.queue.put(incoming)
            self.logger.info(f"Enqueued message: {incoming}")

        self.logger.info("Starting AsyncTeleBot polling...")
        await self.bot.infinity_polling()

    async def send(self, request: Message, response: Message, proof: Optional[Proof] = None):
        """Send a response message back to the Telegram chat.

        Args:
            request (Message): The original request message (unused)
            response (Message): The response to send to Telegram

        Note:
            The response must include a valid conversation_id that matches
            the Telegram chat ID where the response should be sent.

        Raises:
            Warning: If no conversation_id is found in the response
        """
        if not response.conversation_id:
            self.logger.warning("No conversation_id found in request; cannot respond.")
            return

        chat_id = response.conversation_id

        await self.bot.send_message(chat_id, response.content)
        self.logger.info(f"Posted output to chat {chat_id}: {response.content}")
