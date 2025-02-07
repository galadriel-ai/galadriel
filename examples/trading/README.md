# Trading Agent Example

## Description
This example shows an agent that fetches trending coins, gets market data, does analysis and swaps token.
It uses:
- `gpt-4o` model from OpenAI
- [CodeAgent](https://huggingface.co/docs/smolagents/reference/agents#smolagents.CodeAgent) from `smolagents` which performs a series of steps until it reaches the final result
- `Cron` which schedules the agent to run at specified intervals.
- `AgentRuntime` which connects the client to agent and runs the agent execution
- `tools` which contains tools that the agent can call to perform specific tasks. For example, `coingecko.fetch_trending_coins` fetches the top trending coins from CoinGecko API. For details on the tools, see the [tools](../../galadriel/tools/) directory.

## How the agent works
- Starts a cron job that runs every 5 minutes.
- Fetches the top trending coins from CoinGecko and Dexscreener APIs.
- Fetches the market data for the specified token.
- Uses the `gpt-4o` model to generate a strategy based on the market data.
    - If the strategy is to buy or sell, it calls the Jupiter or Raydium API to place the order.
    - If the strategy is to hold, it does nothing.

## Running the agent
1. Setup local env and install dependencies.
```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Rename `template.env` to `.env` and add your OpenAI API and Coingecko API keys.
3. Rename `template.agents.env` to `agents.env` and add your solana keypair address.
4. Run the agent.
```shell
python agent.py
```