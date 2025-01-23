# Galadriel Agent

## Setup
```shell
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
# or 
pip install -e .

cp template.env .env
nano .env
```

## Run an agent
This takes the agent definition from `agents/daige.json`
```shell
python main.py
```
Can also run in docker
```shell
docker compose up --build
```


## Linting etc
```shell
source toolbox.sh
lint
format
type-check
```

## Testing
Ensure that dev dependencies are installed
```shell
source toolbox.sh
unit-test
```


## Deployment

```shell
./deploy.sh
```

## Before using CLI - IMPORTANT

After running `agent init` you'll need:
1.  to copy the `galadriel-agent` folder to the root of the project.
2. add the following line to `docker-compose.yml`, inside the `volumes` section:
    ```
    - ./galadriel-agent:/home/appuser/galadriel-agent
    ```
explanation:
- galadriel-agent is not yet a package, so we need to mount it as a volume inside the docker container.
- this is a temporary solution until the package is published on pypi.


# Galadriel Agent CLI

Command-line interface for creating, building, and managing Galadriel agents.

## Commands

### Initialize a New Agent
Create a new agent project with all necessary files and structure.
```
agent init
```
This will prompt you for:
- Agent name
- Docker username
- Docker password
- Galadriel API key

The command creates:
- Basic agent structure
- Docker configuration
- Environment files
- Required Python files

### Build Agent
Build the Docker image for your agent.
```
agent build [--image-name NAME]
```
Options:
- `--image-name`: Name for the Docker image (default: "agent")

### Publish Agent
Push the agent's Docker image to Docker Hub.
```
agnet publish [--image-name NAME]
```
Options:
- `--image-name`: Name for the Docker image (default: "agent")

### Deploy Agent
Deploy the agent to the Galadriel platform.
```
agent deploy [--image-name NAME]
```
Options:
- `--image-name`: Name for the Docker image (default: "agent")

### Get Agent State
Retrieve the current state of a deployed agent.
```
agnet state --agent-id AGENT_ID
```
Required:
- `--agent-id`: ID of the deployed agent

### List All Agents
Get information about all deployed agents.
```
galadriel states
```

### Destroy Agent
Remove a deployed agent from the Galadriel platform.
```
agent destroy AGENT_ID
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