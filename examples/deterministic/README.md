# Deterministic Agent Example

This is an example of deterministic Twitter "agent" that posts on twitter every 3 hours.
It has a cron job that triggers every 3 hours and generates a Twitter post
that is then posted on Twitter through its official API.

## Why deterministic?

The _agency_ of agents exists on a spectrum. The more agentic an agent is, the more its behavior is influenced by the LLM. 
However, there is a tradeoff—LLM execution is probabilistic, meaning it may not always produce the same behavior. 
In some cases, a developer may prefer a more deterministic approach to ensure consistency.

In this example, the developer chose to make the Twitter agent follow a fixed process in each iteration of the loop:
1. Retrieve the content of the tweet from the LLM.
2. Post the tweet.

Allowing the LLM to make probabilistic decisions in this scenario would only increase costs and reduce the reliability of the desired flow.
At the same time, the developer still wanted to leverage key functionalities of the framework, such as tooling, orchestration (`Cron`), and more.

## Features

- 🤖 Works automatically with no user input
- 🌤️ Posts tweets using a Twitter Client

## Framework Components Used

This example demonstrates several key features of the Galadriel framework:

- `Cron`: Triggers agent actions at a configured interval
- `Agent`: Implements the base Agent interface for a custom "agent" implementation
- `LiteLLMModel`: Integration with language models via LiteLLM
- Custom tools:
    - Composio Weather API (converted using `convert_action`)
    - Time tool
- `TwitterPostClient`: A client for posting Tweets on Twitter

## Setup and Running

1. Setup local env and install `galadriel`.

```bash
```shell
pip install -r requirements.txt
python3 -m venv venv
source venv/bin/activate
pip install galadriel
```

2. Rename `template.env` to `.env` and add your OpenAI API key
   along with credentials for Twitter.

```bash
OPENAI_API_KEY=

# Under "Consumer Keys"
TWITTER_CONSUMER_API_KEY=
TWITTER_CONSUMER_API_SECRET=
# Under "Authentication Tokens -> "Access Token and Secret" (requires Write permission)
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=
```

Check out https://developer.x.com/, for these values.
User authentication needs to be set up with write access.


You can also include something like

```bash
DRY_RUN=true
```

in your `.env` to skip the actual Twitter posting part, just to see
what the Agent would have posted. This can be useful for testing and
modifying the prompt.

4. Run the agent:

```bash
python twitter_agent.py
```
