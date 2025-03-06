# Intent Router Agent Example

## Description

This example demonstrates an intent routing system that analyzes user requests and directs them to specialized agents. It uses:

- `gpt-4o` model from OpenAI
- [ToolCallingAgent](https://github.com/galadriel-ai/galadriel/blob/main/galadriel/agent.py) as the main router that analyzes user intent
- Two specialized [CodeAgent](https://github.com/galadriel-ai/galadriel/blob/main/galadriel/agent.py) instances:
  - `calculator_agent` for handling calculation-related requests
  - `sentiment_agent` for handling all other types of requests
- `TerminalClient` which implements both input and output interfaces for terminal interaction
- `AgentRuntime` which connects the client to the agent and runs the execution
- `MemoryStore` to maintain conversation history

The intent router analyzes each user request, determines the appropriate specialized agent to handle it, and returns the response from that agent.

## Running the agent

1. Setup local env and install `galadriel`.

```shell
python3 -m venv venv
source venv/bin/activate
pip install galadriel
```

2. Install additional dependencies:

```shell
pip install python-dotenv
```

3. Rename `template.env` to `.env` and add your OpenAI API Key.
4. Run the agent.

```shell
python agent.py
```

## How it works

1. The intent router analyzes the user's request to identify the primary intent
2. It selects the most appropriate specialized agent:
   - `calculator_agent` for math and calculation requests
   - `sentiment_agent` for all other types of requests
3. The request is routed to the selected agent
4. The response from the specialized agent is returned to the user

This architecture demonstrates how to build a modular agent system where specialized agents handle different types of tasks.