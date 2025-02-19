# Galadriel

Galadriel is a Python framework for building autonomous, economically useful AI Agents.

## Quickstart
Note: you should setup local env for this. In terminal
```shell
python3 -m venv venv
source venv/bin/activate
```

And then, install `galadriel` package.
```shell
pip install galadriel
```

Now, create a new python file and copy the code below to create sample agent.
It uses `TestClient` which sends 2 messages sequentially to the agent and prints the result of agent execution.

```python
import asyncio
from galadriel import AgentRuntime, CodeAgent, LiteLLMModel
from galadriel.clients import SimpleMessageClient
from galadriel.tools import DuckDuckGoSearchTool

model = LiteLLMModel(model_id="gpt-4o", api_key="<ADD YOUR OPENAI KEY HERE>")

agent = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool()]
)

client = SimpleMessageClient("Explain the concept of blockchain")

runtime = AgentRuntime(
    agent=agent,
    inputs=[client],
    outputs=[client],
)
asyncio.run(runtime.run())
```

## Components

### Clients  
Clients serve as the bridge between agents and external data sources, handling both input and output operations. An input client (`AgentInput`) supplies messages to the agent, while an output client (`AgentOutput`) delivers the agent’s responses to their intended destination. This modular design allows seamless integration with a variety of sources, from scheduled jobs (like cron tasks) to interactive applications (such as Discord bots).

### Tools  
Tools extend an agent’s capabilities by providing predefined functions that enable interaction with external APIs, data sources, and systems. These tools empower agents to perform tasks such as fetching real-time weather updates or submitting blockchain transactions. Each tool defines its name, purpose, input requirements, and output format, ensuring structured and meaningful interactions. Galadriel supports any tool from HuggingFace, Composio and Langchain out-of-the-box.

### Agents  
Agents are the core intelligence behind the system, capable of reasoning, processing inputs, and generating informed responses. Our framework supports ToolCallingAgent and CodeAgent, which build upon Hugging Face’s [Smolagents](https://github.com/huggingface/smolagents) while introducing enhancements for improved integration with the runtime. Agents leverage ReAct-based reasoning and can access a wide variety of LLMs via [LiteLLM](https://www.litellm.ai/). Additionally, they can be configured with custom personalities and interact with powerful tools to enhance their decision-making capabilities.

### Runtime  
The Agent Runtime ensures continuous and autonomous agent execution. It manages the lifecycle of agent interactions, efficiently processing incoming requests while maintaining agent state. The runtime follows a structured execution loop:

1. **Receive a Message** – An input client sends a message to the runtime.
2. **Process the Message** – The agent receives and handles the request.
3. **Send the Response** – The agent's output is forwarded to the appropriate client.
4. **Repeat** – The runtime continuously handles incoming messages in a loop.

This architecture enables real-time, scalable, and efficient agent operations across diverse environments.
