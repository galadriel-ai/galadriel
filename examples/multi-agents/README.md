# Multi-Agent Example

## Description

This example demonstrates a manager-worker pattern using multiple agents. It uses:

- `gpt-4o` model from OpenAI
- A manager `CodeAgent` that coordinates with a specialized worker agent
- A worker agent specialized in web searches using `DuckDuckGoSearchTool`
- `SimpleMessageClient` which implements
  - `AgentInput` to send predefined messages to the agent
  - `AgentOutput` to receive results from the agent and print them
- `AgentRuntime` which connects the client to agent and runs the agent execution

The manager agent can delegate web search tasks to the worker agent, demonstrating how multiple agents can collaborate to accomplish tasks.

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

## Architecture

The example consists of two agents:
- **Manager Agent**: The main agent that receives user queries and coordinates with the worker agent
- **Web Search Agent**: A specialized worker agent equipped with `DuckDuckGoSearchTool` for performing web searches

When a user sends a query, the manager agent can delegate web search tasks to the worker agent when needed, demonstrating hierarchical agent collaboration.