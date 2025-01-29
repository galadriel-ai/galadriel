from datetime import datetime
import logging

from typing import Optional
from telebot import types

from galadriel_agent.agent import AgentInput, AgentOutput
from galadriel_agent.entities import Message, HumanMessage, PushOnlyQueue

from telebot.async_telebot import AsyncTeleBot


class TelegramClient(AgentInput, AgentOutput):
    def __init__(self, token: str, logger: logging.Logger):
        self.token = token
        self.bot = AsyncTeleBot(token)
        self.queue: Optional[PushOnlyQueue] = None
        self.logger = logger

    async def start(self, queue: PushOnlyQueue) -> None:
        self.queue = queue

        @self.bot.message_handler(func=lambda message: True)
        async def handle_incoming_message(message: types.Message):
            if not self.queue:
                self.logger.warning("Queue not initialized. Ignoring incoming message.")
                return
            user = message.from_user
            author = (
                f"{user.first_name} {user.last_name}".strip()
                if user.first_name
                else user.username or str(user.id)
            )
            incoming = HumanMessage(
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

    async def send(self, request: Message, response: Message, proof: str):
        if not response.conversation_id:
            self.logger.warning("No conversation_id found in request; cannot respond.")
            return

        chat_id = response.conversation_id

        await self.bot.send_message(chat_id, response.content)
        self.logger.info(f"Posted output to chat {chat_id}: {response.content}")
