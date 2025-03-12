# Galadriel Agent CLI

Command-line interface for creating, building, and deploying autonomous agents to Galadriel's agent network. This tool helps you manage the entire agent lifecycle - from initialization and development to deployment and monitoring. It also provides wallet management commands for creating and managing Solana wallets to interact with the Galadriel network.

## Setup

### Installation

Install the Galadriel package using pip:

```bash
pip install galadriel
```

## Agent Commands

### Initialize a New Agent
Create a new agent project with all necessary files and structure.
```
galadriel agent init
```
This will prompt you for:
- Agent name

The command creates:
- Basic agent structure
- Docker configuration
- Environment files
- Required Python files

### Build Agent
Build the Docker image for your agent.
```
galadriel agent build [--image-name NAME]
```
Options:
- `--image-name`: Name for the Docker image (default: "agent")

### Publish Agent
Push the agent's Docker image to Docker Hub.
```
galadriel agent publish [--image-name NAME]
```
Options:
- `--image-name`: Name for the Docker image (default: "agent")

### Deploy Agent
Build, publish and deploy the agent to the Galadriel platform.
```
galadriel agent deploy [--image-name NAME] [--skip-build] [--skip-publish]
```
Options:
- `--image-name`: Name for the Docker image (default: "agent")
- `--skip-build`: Skip building the Docker image
- `--skip-publish`: Skip publishing the Docker image to Docker Hub

### Update Agent
Update an existing agent on the Galadriel platform.
```
galadriel agent update --agent-id AGENT_ID [--image-name NAME]
```
Options:
- `--agent-id`: ID of the agent to update
- `--image-name`: Name for the Docker image (default: "agent")

### Get Agent State
Retrieve the current state of a deployed agent.
```
galadriel agent state --agent-id AGENT_ID
```
Required:
- `--agent-id`: ID of the deployed agent

### List All Agents
Get information about all deployed agents.
```
galadriel agent list
```

### Destroy Agent
Remove a deployed agent from the Galadriel platform.
```
galadriel agent destroy AGENT_ID
```
Required:
- `AGENT_ID`: ID of the agent to destroy

## Wallet Commands

### Create Wallet
Create a new Solana wallet.
```
galadriel wallet create [--path PATH]
```
Options:
- `--path`: Path to save the wallet key file (default: "~/.galadriel/solana/default_key.json")

### Import Wallet
Import an existing wallet.
```
galadriel wallet import [--private-key KEY] [--path PATH]
```
Options:
- `--private-key`: Private key of the wallet to import in JSON format
- `--path`: Path to the wallet key file to import

Note: You must provide either `--private-key` or `--path`, but not both.

### Request Airdrop
Request an airdrop of 0.001 SOL to your Solana wallet.
```
galadriel wallet airdrop
```

## Configuration Files

### .env
Required environment variables for deployment:
```
DOCKER_USERNAME=your_username
DOCKER_PASSWORD=your_password
GALADRIEL_API_KEY=your_api_key
```

### .agents.env
Environment variables for the agent runtime (do not include deployment credentials):
```
# Example
LLM_API_KEY=your_key
LLM_MODEL=your_model
SOLANA_KEY_PATH=path_to_your_solana_key
```

## Examples

Create and deploy a new agent:
```
# Initialize new agent
galadriel agent init

# Build and deploy
galadriel agent deploy --image-name my-agent

# Check agent status
galadriel agent state --agent-id your-agent-id
```

Create and manage a wallet:
```
# Create a new wallet
galadriel wallet create

# Request an airdrop
galadriel wallet airdrop
```

## Error Handling

- All commands will display detailed error messages if something goes wrong
- Check your `.env` and `.agents.env` files if you encounter authentication issues
- Ensure Docker is running before using build/publish commands
- Verify your Galadriel API key is valid for deployment operations

## Notes

- Make sure Docker is installed and running for build/publish operations
- Ensure you have necessary permissions on Docker Hub
- Keep your API keys and credentials secure
- Don't include sensitive credentials in `.agents.env`