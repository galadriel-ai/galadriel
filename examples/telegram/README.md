# Telegram Elon Musk Agent Example

A Telegram bot that simulates Elon Musk's personality, capable of interacting with users in a Telegram chat. The bot can provide weather information and tell the current time while maintaining Elon's characteristic communication style.

## Features

- 🤖 Responds to messages in Telegram chats with Elon Musk's personality
- 🌤️ Can check weather conditions using the Composio Weather API
- ⏰ Provides current time information
- 🔄 Maintains context and can engage in multi-turn conversations

## Framework Components Used

This example demonstrates several key features of the Galadriel framework:

- `TelegramClient`: Handles Telegram message input/output
- `ToolCallingAgent`: Base agent class for handling tool-based interactions
- `LiteLLMModel`: Integration with language models via LiteLLM
- Custom tools:
  - Composio Weather API (converted using `convert_action`)
  - Time tool

## Setup and Running

1. Setup local env and install `galadriel`.

```shell
python3 -m venv venv
source venv/bin/activate
pip install galadriel
```

2. Create a `.env` file with the following variables:

```bash
OPENAI_API_KEY=
TELEGRAM_TOKEN=
COMPOSIO_API_KEY=
```

3. Make sure you have the `agent.json` file in the same directory, which defines Elon Musk's personality traits.

4. Run the agent:

```bash
python telegram_agent.py
```


## Telegram Bot Setup

Follow the instructions in this [Telegram Bot Tutorial](https://www.directual.com/lesson-library/how-to-create-a-telegram-bot) to create a new bot and get a token.