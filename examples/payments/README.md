# Researcher Agent

## Description

This example demonstrates a research agent that requires **SOL payments** from users before executing tasks. The agent is designed to analyze investment-related queries and retrieve relevant data from Web3 tools. It uses:

- **gpt-4o model** from OpenAI for language processing.
- **CodeAgent** from [smolagents](https://huggingface.co/docs/smolagents/reference/agents#smolagents.CodeAgent) to execute a series of steps for reaching a final result.
- **AgentRuntime** to connect various clients to the agent and execute the agent logic.
- **Clients**:
  - **TwitterMentionClient** (commented out by default) for processing mentions on Twitter.
  - **SimpleMessageClient** as a local test client with predefined messages.
- **Web3 Tools**:
  - **get_coin_price** from CoinGecko to fetch real-time cryptocurrency prices.
  - **get_token_profile** from DexScreener to retrieve token profiles.
- **Pricing Mechanism**, requiring users to pay in **Solana (SOL)** to the agent's wallet before the agent executes the task.

### Payment and Transaction Requirements

The client must provide a task with one of the following:

- A **link to a Solana transaction** (e.g., from Solscan)
- A **transaction signature** on the Solana blockchain

## Running the agent

1. Setup local env and install `galadriel`.

```shell
python3 -m venv venv
source venv/bin/activate
pip install galadriel
```

2. Create an **agent wallet** where the agent will receive SOL payments.

3. Rename `template.env` to `.env` and add your agent wallet address and OpenAI API key along with credentials for Twitter if needed.

4. Configure the agent wallet for receiving **SOL payments**.

5. Run the agent:

   ```sh
   python agent.py
   ```

By default, the script includes a test client (`SimpleMessageClient`). If you want to enable Twitter integration, uncomment the corresponding section in `agent.py` and provide the required API credentials in the `.env` file.
