# Web3 Example

## Description

This example demonstrates an agent which checks market data for a specific token.
It uses:

- `gpt-4o` model from OpenAI
- [CodeAgent](https://huggingface.co/docs/smolagents/reference/agents#smolagents.CodeAgent) from `smolagents` which performs a series of steps until it reaches the final result
- `SimpleMessageClient` which simulates user input in the form of market-related question
- `AgentRuntime` which connects the client to agent and runs the agent execution
- `dexscreener.fetch_market_data` Web3 tool which fetches market data for top tokens

Returns the response similar to this one:

```
Question: What are top tokens on the market today?
Answer: The top tokens by 24-hour volume are: 'Trump's Tax Company', 'dogwifouthat', 'THE DARK KNIGHT', and 'BRITISH DOG'

Question: Should I buy ETH?
Answer: Consider buying ETH if you are comfortable with its recent volatility and believe in its long-term potential, but ensure your decision aligns with your financial goals and risk tolerance.
```

## Running the agent

1. Setup local env and install `galadriel`.

```shell
python3 -m venv venv
source venv/bin/activate
pip install galadriel
```

2. Rename `template.env` to `.env` and add your OpenAI API Key.
3. Run the agent.

```shell
python agent.py
```
