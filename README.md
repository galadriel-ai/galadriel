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
from galadriel import AgentRuntime, CodeAgent
from galadriel.clients import SimpleMessageClient
from galadriel.core_agent import LiteLLMModel, DuckDuckGoSearchTool

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