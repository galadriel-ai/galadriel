# Discord Elon Musk Agent Example

A Discord bot that simulates Elon Musk's personality, capable of interacting with users in a Discord server. The bot can provide weather information and tell the current time while maintaining Elon's characteristic communication style.

## Features

- 🤖 Responds to messages in Discord channels with Elon Musk's personality
- 🌤️ Can check weather conditions using the Composio Weather API
- ⏰ Provides current time information
- 🔄 Maintains context and can engage in multi-turn conversations

## Framework Components Used

This example demonstrates several key features of the Galadriel framework:

- `DiscordClient`: Handles Discord message input/output
- `ToolCallingAgent`: Base agent class for handling tool-based interactions
- `LiteLLMModel`: Integration with language models via LiteLLM
- Custom tools:
  - Composio Weather API (converted using `convert_action`)
  - Time tool

## Setup and Running

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with the following variables:

```bash
DISCORD_TOKEN=
DISCORD_APP_ID=
DISCORD_GUILD_ID=
DISCORD_KEY=
OPENAI_API_KEY=
COMPOSIO_API_KEY=
```

3. Make sure you have the `agent.json` file in the same directory, which defines Elon Musk's personality traits.

4. Run the agent:

```bash
python discord_agent.py
```


## Discord Bot Setup

Follow the instructions in the [Discord API documentation](https://discordpy.readthedocs.io/en/stable/discord.html) to create a new application and bot.