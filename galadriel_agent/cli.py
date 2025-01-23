import os
import shutil
import click
import requests
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
from typing import Tuple

API_BASE_URL = "https://api.galadriel.com/v1"

@click.group()
def main():
    """Sentience CLI"""
    pass


@main.command()
def init() -> None:
    """Create a new Agent folder template in the current directory."""
    agent_name = click.prompt("Enter agent name", type=str)
    docker_username = click.prompt("Enter Docker username", type=str)
    docker_password = click.prompt("Enter Docker password", hide_input=True, type=str)
    galadriel_api_key = click.prompt(
        "Enter Galadriel API key", hide_input=True, type=str
    )

    click.echo(f"Creating a new agent template in {os.getcwd()}...")
    try:
        _create_agent_template(
            agent_name, docker_username, docker_password, galadriel_api_key
        )
        click.echo("Successfully created agent template!")
    except Exception as e:
        click.echo(f"Error creating agent template: {str(e)}", err=True)


@main.command()
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


@main.command()
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


@main.command()
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


@main.command()
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


@main.command()
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

@main.command()
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
    agent_configurator_dir = os.path.join(agent_name, "agent_configurator")
    docker_dir = os.path.join(agent_name, "docker")
    os.makedirs(agent_dir, exist_ok=True)
    os.makedirs(agent_configurator_dir, exist_ok=True)
    os.makedirs(docker_dir)

    # Generate <agent_name>.py
    class_name = "".join(word.capitalize() for word in agent_name.split("_"))
    agent_code = f"""from galadriel_agent.agent import UserAgent
from typing import Dict

class {class_name}(UserAgent):
    async def run(self, request: Dict) -> Dict:
        # Implement your agent's logic here
        print(f"Running {class_name} with agent configuration: {{self.agent_config}}")
"""
    with open(os.path.join(agent_dir, f"{agent_name}.py"), "w") as f:
        f.write(agent_code)

    # Generate <agent_name>.json
    initial_data = {
        "name": class_name,
        "description": "A brief description of your agent",
        "prompt": "The initial prompt for the agent",
        "tools": [],
    }
    with open(os.path.join(agent_configurator_dir, f"{agent_name}.json"), "w") as f:
        json.dump(initial_data, f, indent=2)

    # generate main.py
    main_code = f"""import asyncio
from agent.{agent_name} import {class_name}
from galadriel_agent.agent import GaladrielAgent

if __name__ == "__main__":
    {agent_name} = {class_name}()
    client = None
    agent = GaladrielAgent(
        agent_config=None,
        clients=[client], 
        user_agent={agent_name},
        s3_client=None,
    )
    asyncio.run(agent.run())
"""
    with open(os.path.join(agent_name, "main.py"), "w") as f:
        f.write(main_code)


    # Generate pyproject.toml
    pyproject_toml = f"""
[tool.poetry]
name = "agent"
version = "0.1.0"
description = ""
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
galadriel_agent = {{path = "./galadriel-agent"}}

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
"""
    with open(os.path.join(agent_name, "pyproject.toml"), "w") as f:
        f.write(pyproject_toml)

    # Create .env and .agents.env file in the agent directory
    env_content = f"""DOCKER_USERNAME={docker_username}
DOCKER_PASSWORD={docker_password}
GALADRIEL_API_KEY={galadriel_api_key}"""
    with open(os.path.join(agent_name, ".env"), "w") as f:
        f.write(env_content)
    open(os.path.join(agent_name, ".agents.env"), "w").close()

    # copy docker files from sentience/galadriel_agent/docker to user current directory
    docker_files_dir = os.path.join(os.path.dirname(__file__), "docker")
    shutil.copy(
        os.path.join(os.path.join(os.path.dirname(__file__)), "docker-compose.yml"),
        os.path.join(agent_name, "docker-compose.yml"),
    )
    shutil.copy(
        os.path.join(docker_files_dir, "Dockerfile"),
        os.path.join(docker_dir, "Dockerfile"),
    )
    shutil.copy(
        os.path.join(docker_files_dir, "logrotate_logs"),
        os.path.join(docker_dir, "logrotate_logs"),
    )


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


def _galadriel_deploy(image_name: str, docker_username: str) -> str:
    """Deploy agent to Galadriel platform."""

    if not os.path.exists(".agents.env"):
        raise click.ClickException(
            "No .agents.env file found in current directory. Please create one."
        )

    env_vars = dict(dotenv_values('.agents.env'))

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
    else:
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
