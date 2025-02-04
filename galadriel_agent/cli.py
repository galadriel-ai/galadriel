import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from typing import Tuple

import click
import requests
from dotenv import dotenv_values
from dotenv import load_dotenv

# pylint: disable=import-error
from solders.keypair import Keypair

API_BASE_URL = "https://api.galadriel.com/v1"
DEFAULT_SOLANA_KEY_PATH = os.path.expanduser("~/secret/.private_key.json")


@click.group(
    help="""
Galadriel: A CLI tool to create autonomous agents and deploy them to Galadriel L1.

Usage:
  galadriel [resource] [subcommand] [options]

Resources:
  agent     Manage agents (create, update, etc.)

Options:
  -h, --help    Show this help message and exit

For more information about each resource, use:
  galadriel <resource> --help
"""
)
def galadriel():
    pass


@galadriel.group()
def agent():
    """Agent management commands"""


@agent.command()
def init() -> None:
    """Create a new Agent folder template in the current directory."""
    agent_name = ""
    while not agent_name:
        agent_name_input = click.prompt("Enter agent name", type=str)
        agent_name = _sanitize_agent_name(agent_name_input)
        if not agent_name:
            print(
                "Invalid agent name: name should only contain alphanumerical and _ symbols."
            )

    # docker_username = click.prompt("Enter Docker username", type=str)
    # docker_password = click.prompt("Enter Docker password", hide_input=True, type=str)
    # galadriel_api_key = click.prompt(
    #     "Enter Galadriel API key", hide_input=True, type=str
    # )

    click.echo(f"Creating a new agent template in {os.getcwd()}...")
    try:
        _create_agent_template(
            agent_name, "", "", ""
        )
        click.echo("Successfully created agent template!")
    except Exception as e:
        click.echo(f"Error creating agent template: {str(e)}", err=True)


@agent.command()
@click.option("--image-name", default="agent", help="Name of the Docker image")
def build(image_name: str) -> None:
    """Build the agent Docker image."""
    try:
        docker_username, _ = _assert_config_files(image_name=image_name)
        _build_image(docker_username=docker_username)
    except subprocess.CalledProcessError as e:
        raise click.ClickException(f"Docker command failed: {str(e)}")
    except Exception as e:
        raise click.ClickException(str(e))


@agent.command()
@click.option("--image-name", default="agent", help="Name of the Docker image")
def publish(image_name: str) -> None:
    """Publish the agent Docker image to the Docker Hub."""
    try:
        docker_username, docker_password = _assert_config_files(image_name=image_name)
        _publish_image(
            image_name=image_name,
            docker_username=docker_username,
            docker_password=docker_password,
        )
    except subprocess.CalledProcessError as e:
        raise click.ClickException(f"Docker command failed: {str(e)}")
    except Exception as e:
        raise click.ClickException(str(e))


@agent.command()
@click.option("--image-name", default="agent", help="Name of the Docker image")
def deploy(image_name: str) -> None:
    """Build, publish and deploy the agent."""
    try:
        docker_username, docker_password = _assert_config_files(image_name=image_name)

        click.echo("Building agent...")
        _build_image(docker_username=docker_username)

        click.echo("Publishing agent...")
        _publish_image(
            image_name=image_name,
            docker_username=docker_username,
            docker_password=docker_password,
        )

        click.echo("Deploying agent...")
        agent_id = _galadriel_deploy(image_name, docker_username)
        if not agent_id:
            raise click.ClickException("Failed to deploy agent")
        click.echo(f"Successfully deployed agent! Agent ID: {agent_id}")
    except Exception as e:
        raise click.ClickException(str(e))


@agent.command()
@click.option("--agent-id", help="ID of the agent to update")
@click.option("--image-name", default="agent", help="Name of the Docker image")
def update(agent_id: str, image_name: str):
    """Update the agent"""
    click.echo(f"Updating agent {agent_id}")
    try:
        docker_username, _ = _assert_config_files(image_name=image_name)
        status = _galadriel_update(
            image_name=image_name, docker_username=docker_username, agent_id=agent_id
        )
        if status:
            click.echo(f"Successfully updated agent {agent_id}")
        else:
            raise click.ClickException(f"Failed to update agent {agent_id}")
    except Exception as e:
        raise click.ClickException(str(e))


@agent.command()
@click.option("--agent-id", help="ID of the agent to get state for")
def state(agent_id: str):
    """Get information about a deployed agent from Galadriel platform."""
    try:
        load_dotenv(dotenv_path=Path(".") / ".env", override=True)
        api_key = os.getenv("GALADRIEL_API_KEY")
        if not api_key:
            raise click.ClickException("GALADRIEL_API_KEY not found in environment")

        response = requests.get(
            f"{API_BASE_URL}/agents/{agent_id}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        if not response.status_code == 200:
            click.echo(
                f"Failed to get agent state with status {response.status_code}: {response.text}"
            )
        click.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        click.echo(f"Failed to get agent state: {str(e)}")


@agent.command()
def states():
    """Get all agent states"""
    try:
        load_dotenv(dotenv_path=Path(".") / ".env", override=True)
        api_key = os.getenv("GALADRIEL_API_KEY")
        if not api_key:
            raise click.ClickException("GALADRIEL_API_KEY not found in environment")

        response = requests.get(
            f"{API_BASE_URL}/agents/",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        if not response.status_code == 200:
            click.echo(
                f"Failed to get agent state with status {response.status_code}: {response.text}"
            )
        click.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        click.echo(f"Failed to get agent state: {str(e)}")


@agent.command()
@click.argument("agent_id")
def destroy(agent_id: str):
    """Destroy a deployed agent from Galadriel platform."""
    try:
        load_dotenv(dotenv_path=Path(".") / ".env", override=True)
        api_key = os.getenv("GALADRIEL_API_KEY")
        if not api_key:
            raise click.ClickException("GALADRIEL_API_KEY not found in environment")

        response = requests.delete(
            f"{API_BASE_URL}/agents/{agent_id}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        if response.status_code == 200:
            click.echo(f"Successfully destroyed agent {agent_id}")
        else:
            click.echo(
                f"Failed to destroy agent with status {response.status_code}: {response.text}"
            )
    except Exception as e:
        click.echo(f"Failed to destroy agent: {str(e)}")


@galadriel.group()
def wallet():
    """Wallet management commands"""


@wallet.command()
@click.option("--path", default=DEFAULT_SOLANA_KEY_PATH, help="Path to save the wallet key file")
def create(path: str):
    """Create a new admin wallet"""
    try:
        pub_key = _create_solana_wallet(path)
        click.echo(f"Successfully created Solana wallet {pub_key} at {path}")
    except Exception as e:
        click.echo(f"Failed to create Solana wallet: {str(e)}")


@wallet.command(name="import")
@click.option("--private-key", help="Private key of the wallet to import in JSON format")
@click.option("--path", help="Path to the wallet key file to import")
def import_wallet(private_key: str, path: str):
    """Import an existing wallet"""
    if not private_key and not path:
        raise click.ClickException("Please provide either --private-key or --path")

    if private_key and path:
        raise click.ClickException("Please provide only one of --private-key or --path")

    if private_key:
        # Check if the private key is a valid json
        try:
            json.loads(private_key)
        except json.JSONDecodeError:
            raise click.ClickException("Invalid private key! Please provide a valid JSON array")
        # Save the private key to the default path
        os.makedirs(os.path.dirname(DEFAULT_SOLANA_KEY_PATH), exist_ok=True)
        with open(DEFAULT_SOLANA_KEY_PATH, "w") as file:
            file.write(private_key)
        _update_agent_env_file({"SOLANA_PRIVATE_KEY_PATH": DEFAULT_SOLANA_KEY_PATH})

        click.echo(f"Successfully imported Solana wallet from private key")
    elif path:
        if not os.path.exists(path):
            raise click.ClickException(f"File {path} does not exist")
        _update_agent_env_file({"SOLANA_PRIVATE_KEY_PATH": path})

        click.echo(f"Successfully imported Solana wallet from {path}")


def _assert_config_files(image_name: str) -> Tuple[str, str]:
    if not os.path.exists("docker-compose.yml"):
        raise click.ClickException("No docker-compose.yml found in current directory")
    if not os.path.exists(".env"):
        raise click.ClickException("No .env file found in current directory")

    load_dotenv(dotenv_path=Path(".") / ".env", override=True)
    docker_username = os.getenv("DOCKER_USERNAME")
    docker_password = os.getenv("DOCKER_PASSWORD")
    os.environ["IMAGE_NAME"] = image_name  # required for docker-compose.yml
    if not docker_username or not docker_password:
        raise click.ClickException(
            "DOCKER_USERNAME or DOCKER_PASSWORD not found in .env file"
        )
    return docker_username, docker_password


def _get_agent_name() -> Optional[str]:
    if not os.path.exists(".agents.env"):
        raise click.ClickException(
            "No .agents.env file found in current directory. Please create one."
        )
    env_vars = dict(dotenv_values(".agents.env"))
    agent_name = env_vars.get("AGENT_NAME")
    return agent_name


def _create_agent_template(
    agent_name: str, docker_username: str, docker_password: str, galadriel_api_key: str
) -> None:
    """
    Generates the Python code and directory structure for a new Galadriel agent.

    Args:
        agent_name: The name of the agent (e.g., "my_daige").
    """

    # Create directories
    agent_dir = os.path.join(agent_name, "agent")
    # agent_configurator_dir = os.path.join(agent_name, "agent_configurator")
    # docker_dir = os.path.join(agent_name, "docker")
    os.makedirs(agent_dir, exist_ok=True)
    # os.makedirs(agent_configurator_dir, exist_ok=True)
    # os.makedirs(docker_dir)

    # Generate <agent_name>.py
    class_name = "".join(word.capitalize() for word in agent_name.split("_"))
    agent_code = f"""from galadriel_agent.agent import Agent
from galadriel_agent.entities import Message


class {class_name}(Agent):
    async def run(self, request: Message) -> Message:
        # Implement your agent's logic here
        print(f"Running {class_name}")
        return Message(
            content="TODO"
        )
"""
    with open(os.path.join(agent_dir, f"{agent_name}.py"), "w", encoding="utf-8") as f:
        f.write(agent_code)

    # Generate <agent_name>.json
    # initial_data = {
    #     "name": class_name,
    #     "description": "A brief description of your agent",
    #     "prompt": "The initial prompt for the agent",
    #     "tools": [],
    # }
    # with open(
    #     os.path.join(agent_configurator_dir, f"{agent_name}.json"),
    #     "w",
    #     encoding="utf-8",
    # ) as f:
    #     json.dump(initial_data, f, indent=2)

    # generate agent.py
    main_code = f"""import asyncio

from galadriel_agent.agent import AgentOutput
from galadriel_agent.agent import AgentRuntime
from galadriel_agent.clients.cron import Cron
from galadriel_agent.entities import Message

from agent.{agent_name} import {class_name}


class GenericOutput(AgentOutput):

    async def send(self, request: Message, response: Message, proof: str) -> None:
        print(f"Received response: {{response.content}}")


if __name__ == "__main__":
    {agent_name} = {class_name}()
    agent = AgentRuntime(
        inputs=[Cron(interval_seconds=30)],
        outputs=[GenericOutput()],
        agent={agent_name},
    )
    asyncio.run(agent.run())
"""
    with open(os.path.join(agent_name, "agent.py"), "w", encoding="utf-8") as f:
        f.write(main_code)

    # Generate pyproject.toml
    pyproject_toml = """
[tool.poetry]
name = "agent"
version = "0.1.0"
description = ""
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
galadriel = "^0.0.2"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
"""
    with open(os.path.join(agent_name, "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write(pyproject_toml)

    # Create .env and .agents.env file in the agent directory
    #     env_content = f"""DOCKER_USERNAME={docker_username}
    # DOCKER_PASSWORD={docker_password}
    # GALADRIEL_API_KEY={galadriel_api_key}"""
    #     with open(os.path.join(agent_name, ".env"), "w", encoding="utf-8") as f:
    #         f.write(env_content)
    agent_env_content = f'AGENT_NAME="{agent_name}"'
    with open(os.path.join(agent_name, ".agents.env"), "w", encoding="utf-8") as f:
        f.write(agent_env_content)

    # copy docker files from sentience/galadriel_agent/docker to user current directory
    # docker_files_dir = os.path.join(os.path.dirname(__file__), "docker")
    # shutil.copy(
    #     os.path.join(os.path.join(os.path.dirname(__file__)), "docker-compose.yml"),
    #     os.path.join(agent_name, "docker-compose.yml"),
    # )
    # shutil.copy(
    #     os.path.join(docker_files_dir, "Dockerfile"),
    #     os.path.join(docker_dir, "Dockerfile"),
    # )
    # shutil.copy(
    #     os.path.join(docker_files_dir, ".dockerignore"),
    #     os.path.join(agent_name, ".dockerignore"),
    # )
    # shutil.copy(
    #     os.path.join(docker_files_dir, "logrotate_logs"),
    #     os.path.join(docker_dir, "logrotate_logs"),
    # )


def _build_image(docker_username: str) -> None:
    """Core logic to build the Docker image."""
    click.echo(
        f"Building Docker image with tag {docker_username}/{os.environ['IMAGE_NAME']}..."
    )
    subprocess.run(["docker-compose", "build"], check=True)
    click.echo("Successfully built Docker image!")


def _publish_image(image_name: str, docker_username: str, docker_password: str) -> None:
    """Core logic to publish the Docker image to the Docker Hub."""

    # Login to Docker Hub
    click.echo("Logging into Docker Hub...")
    login_process = subprocess.run(
        ["docker", "login", "-u", docker_username, "--password-stdin"],
        input=docker_password.encode(),
        capture_output=True,
    )
    if login_process.returncode != 0:
        raise click.ClickException(
            f"Docker login failed: {login_process.stderr.decode()}"
        )

    # Create repository if it doesn't exist
    click.echo(
        f"Creating repository {docker_username}/{image_name} if it doesn't exist..."
    )
    create_repo_url = (
        f"https://hub.docker.com/v2/repositories/{docker_username}/{image_name}"
    )
    token_response = requests.post(
        "https://hub.docker.com/v2/users/login/",
        json={"username": docker_username, "password": docker_password},
    )
    if token_response.status_code == 200:
        token = token_response.json()["token"]
        requests.post(
            create_repo_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"JWT {token}",
            },
            json={"name": image_name, "is_private": False},
        )
    # Push image to Docker Hub
    click.echo(f"Pushing Docker image {docker_username}/{image_name}:latest ...")
    subprocess.run(
        ["docker", "push", f"{docker_username}/{image_name}:latest"], check=True
    )

    click.echo("Successfully pushed Docker image!")


def _galadriel_deploy(image_name: str, docker_username: str) -> Optional[str]:
    """Deploy agent to Galadriel platform."""

    if not os.path.exists(".agents.env"):
        raise click.ClickException(
            "No .agents.env file found in current directory. Please create one."
        )

    env_vars = dict(dotenv_values(".agents.env"))

    load_dotenv(dotenv_path=Path(".") / ".env")
    api_key = os.getenv("GALADRIEL_API_KEY")
    if not api_key:
        raise click.ClickException("GALADRIEL_API_KEY not found in environment")

    payload = {
        "name": image_name,
        "docker_image": f"{docker_username}/{image_name}:latest",
        "env_vars": env_vars,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "accept": "application/json",
    }
    response = requests.post(
        f"{API_BASE_URL}/agents/",
        json=payload,
        headers=headers,
    )

    if response.status_code == 200:
        agent_id = response.json()["agent_id"]
        return agent_id
    error_msg = f"""
Failed to deploy agent:
Status Code: {response.status_code}
Response: {response.text}
Request URL: {response.request.url}
Request Headers: {dict(response.request.headers)}
Request Body: {response.request.body}
"""
    click.echo(error_msg)
    return None


def _galadriel_update(image_name: str, docker_username: str, agent_id: str) -> bool:
    """Update agent on Galadriel platform."""

    if not os.path.exists(".agents.env"):
        raise click.ClickException(
            "No .agents.env file found in current directory. Please create one."
        )

    env_vars = dict(dotenv_values(".agents.env"))

    load_dotenv(dotenv_path=Path(".") / ".env")
    api_key = os.getenv("GALADRIEL_API_KEY")
    if not api_key:
        raise click.ClickException("GALADRIEL_API_KEY not found in environment")

    payload = {
        "name": image_name,
        "docker_image": f"{docker_username}/{image_name}:latest",
        "env_vars": env_vars,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "accept": "application/json",
    }
    response = requests.put(
        f"{API_BASE_URL}/agents/{agent_id}",
        json=payload,
        headers=headers,
    )

    if response.status_code == 200:
        return True
    else:
        error_msg = f"""
Failed to update agent:
Status Code: {response.status_code}
Response: {response.text}
Request URL: {response.request.url}
Request Headers: {dict(response.request.headers)}
Request Body: {response.request.body}
"""
        click.echo(error_msg)
        return False


def _sanitize_agent_name(user_input: str) -> str:
    """
    Sanitizes the user input to create a valid folder name.
    Allows only alphanumeric characters and underscores (_).
    Other characters are replaced with underscores.

    :param user_input: The raw folder name input from the user.
    :return: A sanitized string suitable for a folder name.
    """
    sanitized_name = re.sub(
        r"\W+", "_", user_input
    )  # Replace non-alphanumeric characters with _
    sanitized_name = sanitized_name.strip("_")  # Remove leading/trailing underscores
    return sanitized_name


def _update_agent_env_file(env_vars: dict) -> None:
    """Update the .agents.env file with the new environment variables."""
    existing_env_vars = dotenv_values(".agents.env")

    # Update existing values or add new ones
    existing_env_vars.update(env_vars)

    agent_env_content = ""
    for key, value in existing_env_vars.items():
        # Wrap the string value in quotes
        if isinstance(value, str):
            value = f'"{value}"'
        agent_env_content += f"\n{key}={value}"

    with open(".agents.env", "w", encoding="utf-8") as f:
        f.write(agent_env_content)


def _create_solana_wallet(path: str) -> str:
    """Create a new Solana wallet and save the private key to a file."""
    # Check if the file already exists to prevent overwriting
    if os.path.exists(path):
        raise click.ClickException(f"File {path} already exists")

    # Update the .agents.env file with the new wallet path
    _update_agent_env_file({"SOLANA_PRIVATE_KEY_PATH": path})

    keypair = Keypair()
    private_key_json = json.dumps(keypair.to_json()).encode("utf-8")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as file:
        file.write(private_key_json)

    return str(keypair.pubkey())
