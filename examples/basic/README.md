# Basic example

## Description

This example demonstrates an agent which receives and processes a sequence of messages. It uses:

- `gpt-4o` model from OpenAI
- [CodeAgent](https://huggingface.co/docs/smolagents/reference/agents#smolagents.CodeAgent) from `smolagents` which performs a series of steps until it reaches the final result
- `SimpleMessageClient` which implements
  - `AgentInput` to infinitely send predefined messages to the agent
  - `AgentOutput` to receive results from the agent and print them
- `AgentRuntime` which connects the client to agent and runs the agent execution
- `DuckDuckGoSearchTool` tool used to browse the web

The agent produces sequentially the answers to given questions.

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
