# Galadriel Agent

## Setup
```shell
pip install galadriel
galadriel agent init
```

## Run your agent
```shell
cd {your_agent_name}
python agent.py
```

# Galadriel Agent CLI

Command-line interface for creating, building, and managing Galadriel agents.

## Commands

### Initialize a New Agent
Create a new agent project with all necessary files and structure.
```
galadriel agent init
```
This will prompt you for:
- Agent name
- Docker username (can set up with random values to start off with)
- Docker password (can set up with random values to start off with)
- Galadriel API key

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
Deploy the agent to the Galadriel platform.
```
galadriel agent deploy [--image-name NAME]
```
Options:
- `--image-name`: Name for the Docker image (default: "agent")

### Update Agent
Update an existing agent on the Galadriel platform.
```
galadriel agent update [--image-name NAME] [--agent-id AGENT_ID]
```
Options:
- `--image-name`: Name for the Docker image (default: "agent")
- `--agent-id`: ID of the agent to update

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
galadriel agent states
```

### Destroy Agent
Remove a deployed agent from the Galadriel platform.
```
galadriel agent destroy AGENT_ID
```
Required:
- `AGENT_ID`: ID of the agent to destroy

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
OPENAI_API_KEY=your_key
DATABASE_URL=your_url
```

## Examples

Create and deploy a new agent:
```
# Initialize new agent
galadriel init

# Build and deploy
galadriel deploy --image-name my-agent

# Check agent status
galadriel state --agent-id your-agent-id
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