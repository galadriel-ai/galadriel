import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List
from typing import Optional
from typing import Tuple

import click
import requests
from dotenv import dotenv_values
from dotenv import load_dotenv

# pylint: disable=import-error
from solders.keypair import Keypair  # type: ignore

API_BASE_URL = "https://api.galadriel.com/v1"
DEFAULT_SOLANA_KEY_PATH = os.path.expanduser("~/.galadriel/solana/default_key.json")
REQUEST_TIMEOUT = 180  # seconds


@click.group(
    help="""
A CLI tool to create autonomous agents and deploy them to Galadriel's decentralized agent network.
"""
)
def galadriel():
    pass


# ===== AGENT COMMANDS =====
@galadriel.group()
def agent():
    """Agent management commands"""
    pass


@agent.command()
def init() -> None:
    """Create a new Agent folder template in the current directory."""
    agent_name = ""
    while not agent_name:
        agent_name_input = click.prompt("Enter agent name", type=str)
        agent_name = _sanitize_agent_name(agent_name_input)
        if not agent_name:
            print("Invalid agent name: name should only contain alphanumerical and _ symbols.")

    click.echo(f"Creating a new agent template in {os.getcwd()}...")
    try:
        _create_agent_template(agent_name)
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
@click.option("--skip-build", is_flag=True, default=False, help="Skips building Agent's Docker image.")
@click.option(
    "--skip-publish", is_flag=True, default=False, help="Skips publishing Agent's Docker image to Docker Hub."
)
def deploy(image_name: str, skip_build: bool, skip_publish: bool) -> None:
    """Build, publish and deploy the agent."""

    if not os.path.exists(".agents.env"):
        raise click.ClickException(
            "Agent requires .agents.env which contains all environment variables the Agent will use when it runs in the network. This file is missing. Rename .template.agents.env or create your own."
        )

    load_dotenv(dotenv_path=Path(".") / ".env")
    galadriel_api_key = os.getenv("GALADRIEL_API_KEY")
    if not galadriel_api_key:
        raise click.ClickException("GALADRIEL_API_KEY not found in environment")

    try:
        docker_username, docker_password = _assert_config_files(image_name=image_name)

        if not skip_build:
            click.echo("Building agent...")
            _build_image(docker_username=docker_username)

        if not skip_publish:
            click.echo("Publishing agent...")
            _publish_image(
                image_name=image_name,
                docker_username=docker_username,
                docker_password=docker_password,
            )

        click.echo("Deploying agent to Galadriel network...")
        agent_id = _galadriel_deploy(image_name, docker_username, galadriel_api_key)
        if not agent_id:
            raise click.ClickException("Failed to deploy agent")
        click.echo(f"Successfully deployed agent! Agent ID: {agent_id}")
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
            timeout=REQUEST_TIMEOUT,
        )

        if not response.status_code == 200:
            click.echo(f"Failed to get agent state with status {response.status_code}: {response.text}")
        click.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        click.echo(f"Failed to get agent state: {str(e)}")


@agent.command()
@click.option("--agent-id", help="ID of the agent to update metadata for")
def metadata(agent_id: str):
    """Update metadata for a deployed agent."""
    load_dotenv(dotenv_path=Path(".") / ".env", override=True)
    api_key = os.getenv("GALADRIEL_API_KEY")
    if not api_key:
        raise click.ClickException("GALADRIEL_API_KEY not found in environment")

    description = input("Agent description (empty for none): ")
    client_url = input("Agent client URL (empty for none): ")

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "accept": "application/json",
        }
        response = requests.post(
            f"{API_BASE_URL}/agents/{agent_id}/configure",
            json={
                "description": description,
                "client_url": client_url,
            },
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if not response.status_code == 200:
            click.echo(f"Failed to get agent state with status {response.status_code}: {response.text}")
        else:
            click.echo("Agent metadata successfully updated.")
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
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 200:
            click.echo(f"Successfully destroyed agent {agent_id}")
        else:
            click.echo(f"Failed to destroy agent with status {response.status_code}: {response.text}")
    except Exception as e:
        click.echo(f"Failed to destroy agent: {str(e)}")


@agent.command()
@click.option("--agent-id", help="ID of the agent to update")
@click.option("--image-name", default="agent", help="Name of the Docker image")
def update(agent_id: str, image_name: str):
    """Update the agent"""
    click.echo(f"Updating agent {agent_id}")
    try:
        docker_username, _ = _assert_config_files(image_name=image_name)
        status = _galadriel_update(image_name=image_name, docker_username=docker_username, agent_id=agent_id)
        if status:
            click.echo(f"Successfully updated agent {agent_id}")
        else:
            raise click.ClickException(f"Failed to update agent {agent_id}")
    except Exception as e:
        raise click.ClickException(str(e))


@agent.command(name="list")
def list_agents():
    """Get all your agents in the network"""
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
            timeout=REQUEST_TIMEOUT,
        )

        if not response.status_code == 200:
            click.echo(f"Failed to get agent state with status {response.status_code}: {response.text}")
        click.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        click.echo(f"Failed to list agents: {str(e)}")


# ===== WALLET COMMANDS =====
@galadriel.group()
def wallet():
    """Wallet management commands"""
    pass


@wallet.command()
@click.option("--path", default=DEFAULT_SOLANA_KEY_PATH, help="Path to save the wallet key file")
def create(path: str):
    """Create a new wallet"""
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

    # FIXME Disable this check for now
    # Check if the .agents.env file exists
    # if not os.path.exists(".agents.env"):
    #    raise click.ClickException(
    #        "No .agents.env file found in current directory. Please run this command under your project directory."
    #    )

    if private_key:
        # Check if the private key is a valid json
        try:
            json.loads(private_key)
        except json.JSONDecodeError:
            raise click.ClickException("Invalid private key! Please provide a valid JSON array")
        # Save the private key to the default path
        os.makedirs(os.path.dirname(DEFAULT_SOLANA_KEY_PATH), exist_ok=True)
        with open(DEFAULT_SOLANA_KEY_PATH, "w", encoding="utf-8") as file:
            file.write(private_key)
        _update_agent_env_file({"SOLANA_KEY_PATH": DEFAULT_SOLANA_KEY_PATH})

        click.echo("Successfully imported Solana wallet from private key")
    elif path:
        if not os.path.exists(path):
            raise click.ClickException(f"File {path} does not exist")
        _update_agent_env_file({"SOLANA_KEY_PATH": path})

        click.echo(f"Successfully imported Solana wallet from {path}")


@wallet.command()
def airdrop():
    """Request an airdrop of 0.001 SOL to the given Solana wallet."""

    load_dotenv(dotenv_path=Path(".") / ".agents.env", override=True)

    key_path = os.getenv("SOLANA_KEY_PATH")
    if not key_path or not os.path.exists(key_path):
        raise click.ClickException(
            "SOLANA_KEY_PATH not found in environment or does not exist. Please run `galadriel wallet create` to create a new wallet or `galadriel wallet import` to import an existing wallet."
        )

    try:
        with open(key_path, "r", encoding="utf-8") as file:
            seed = json.load(file)
            pub_key = Keypair.from_bytes(seed).pubkey()
            _request_airdrop(str(pub_key))
    except json.JSONDecodeError:
        raise click.ClickException(f"Invalid JSON format in key file: {key_path}")
    except Exception as e:
        raise click.ClickException(f"Failed to request airdrop: {str(e)}")


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
        raise click.ClickException("DOCKER_USERNAME or DOCKER_PASSWORD not found in .env file")
    return docker_username, docker_password


# pylint: disable=W0613
def _create_agent_template(agent_name: str) -> None:
    """
    Generates the Python code and directory structure for a new Galadriel agent.

    Args:
        agent_name: The name of the agent (e.g., "my_daige").
    """

    # Create directories
    docker_dir = os.path.join(agent_name, "docker")
    os.makedirs(docker_dir, exist_ok=True)

    # generate agent.py
    main_code = f"""import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent, LiteLLMModel
from galadriel.clients import TerminalClient
from galadriel.tools import DuckDuckGoSearchTool

env_path = Path(".") / ".env"
if not env_path.exists():
    print(f"Looks like .env file is missing. Did you forget to create it from template.env?")
    exit(1)

load_dotenv(dotenv_path=Path(".") / ".env", override=True)

if not os.getenv("LLM_API_KEY"):
    print("LLM_API_KEY is missing in your .env file. Please add it and try again.")
    exit(1)

if not os.getenv("LLM_MODEL"):
    print("LLM_MODEL is missing in your .env file. Please add it and try again.")
    exit(1)

model = LiteLLMModel(model_id=os.getenv("LLM_MODEL"), api_key=os.getenv("LLM_API_KEY"))

{agent_name} = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool()],
)

client = TerminalClient()

runtime = AgentRuntime(
    agent={agent_name},
    inputs=[client],
    outputs=[client],
)

asyncio.run(runtime.run())
"""
    with open(os.path.join(agent_name, "agent.py"), "w", encoding="utf-8") as f:
        f.write(main_code)

    galadriel_version = _get_installed_galadriel_version()

    # Generate pyproject.toml
    pyproject_toml = f"""
[tool.poetry]
name = "agent"
version = "0.1.0"
description = ""
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
galadriel = "^{galadriel_version}"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
"""
    with open(os.path.join(agent_name, "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write(pyproject_toml)

    # copy docker files from galadriel/docker to user current directory
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
        os.path.join(docker_files_dir, ".dockerignore"),
        os.path.join(agent_name, ".dockerignore"),
    )
    shutil.copy(
        os.path.join(docker_files_dir, "logrotate_logs"),
        os.path.join(docker_dir, "logrotate_logs"),
    )

    # copy template files from galadriel/templates to user current directory
    shutil.copy(
        os.path.join(os.path.dirname(__file__), "../template.agents.env"),
        os.path.join(agent_name, "template.agents.env"),
    )
    shutil.copy(
        os.path.join(os.path.dirname(__file__), "../template.env"),
        os.path.join(agent_name, "template.env"),
    )


def _build_image(docker_username: str) -> None:
    """Core logic to build the Docker image."""
    image_name = os.environ["IMAGE_NAME"]
    full_image_name = f"{docker_username}/{image_name}"

    click.echo(f"Building Docker image with tag {full_image_name}...")
    subprocess.run(["docker-compose", "build"], check=True)

    # Get additional image information
    try:
        # Get image ID
        result = subprocess.run(
            ["docker", "images", "--format", "{{.ID}}", full_image_name],
            check=True,
            capture_output=True,
            text=True,
        )
        image_id = result.stdout.strip()

        # Get image size
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Size}}", full_image_name],
            check=True,
            capture_output=True,
            text=True,
        )
        image_size = result.stdout.strip()

        click.echo("Agent's Docker image built successfully")
        click.echo("Image details:")
        click.echo(f"  - Repository: {full_image_name}")
        click.echo(f"  - Image ID: {image_id}")
        click.echo(f"  - Size: {image_size}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Warning: Could not retrieve detailed image information: {str(e)}")
        click.echo(f"Image {full_image_name} was built successfully but details are unavailable.")


def _get_image_layer_hashes(image_name: str) -> List[str]:
    """Get the layer hashes of the Docker image and parse its output as JSON."""
    try:
        result = subprocess.run(
            ["docker", "inspect", image_name],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        click.echo(f"Failed to run docker inspect: {exc}", err=True)
        return []

    try:
        inspect_data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        click.echo(f"Failed to parse docker inspect output as JSON: {exc}", err=True)
        raise exc

    # Ensure that inspect_data is a list.
    if not isinstance(inspect_data, list):
        error_msg = f"Unexpected docker inspect output format: expected a list, got {type(inspect_data)}"
        click.echo(error_msg, err=True)
        raise ValueError(error_msg)

    # Check if the list is empty to avoid IndexError.
    if not inspect_data:
        click.echo("docker inspect returned an empty list for the image.", err=True)
        return []

    rootfs = inspect_data[0].get("RootFS", {})
    layers = rootfs.get("Layers")
    if not layers:
        click.echo("No layer hashes found in the Docker image.", err=True)
        return []
    return layers


def _get_image_hash(image_name: str) -> str:
    """Get a combined hash of all the Docker image layers.

    This function first retrieves all the layer hashes using `_get_image_layer_hashes()`.
    It then concatenates them (preserving the order) and computes a SHA-256 hash
    over the resulting string.

    Args:
        image_name: The name of the Docker image to get the hash for.

    Returns:
        A string containing the combined SHA-256 hash.
    """
    layers = _get_image_layer_hashes(image_name)
    if not layers:
        raise click.ClickException("No layer hashes found for the Docker image.")

    # Concatenate all layer hashes into one single string.
    combined_str = "".join(layers)

    # Compute SHA-256 hash of the concatenated string.
    combined_hash = hashlib.sha256(combined_str.encode("utf-8")).hexdigest()
    return combined_hash


def _publish_image(image_name: str, docker_username: str, docker_password: str) -> None:
    """Core logic to publish the Docker image to the Docker Hub."""

    # Get authentication token
    token_response = requests.post(
        "https://hub.docker.com/v2/users/login/",
        json={"username": docker_username, "password": docker_password},
        timeout=REQUEST_TIMEOUT,
    )

    if token_response.status_code != 200:
        raise click.ClickException(f"Failed to authenticate with Docker Hub: {token_response.text}")

    token = token_response.json()["token"]

    # Check if repository exists
    check_repo_response = requests.get(
        f"https://hub.docker.com/v2/repositories/{docker_username}/{image_name}",
        headers={"Authorization": f"JWT {token}"},
        timeout=REQUEST_TIMEOUT,
    )

    if check_repo_response.status_code == 404:
        # Repository doesn't exist, create it
        click.echo(f"Creating repository {docker_username}/{image_name}...")
        create_repo_response = requests.post(
            "https://hub.docker.com/v2/repositories/",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"JWT {token}",
            },
            json={"namespace": docker_username, "name": image_name, "is_private": False},
            timeout=REQUEST_TIMEOUT,
        )

        if create_repo_response.status_code not in [200, 201]:
            click.echo(f"Warning: Failed to create repository: {create_repo_response.text}")
        else:
            click.echo(f"Successfully created repository {docker_username}/{image_name}")
    elif check_repo_response.status_code == 200:
        click.echo(f"Repository {docker_username}/{image_name} already exists")
    else:
        click.echo(f"Warning: Unexpected response when checking repository: {check_repo_response.text}")

    # Push image to Docker Hub
    click.echo(f"Pushing Docker image {docker_username}/{image_name}:latest ...")

    # Login to Docker Hub to publish the image

    click.echo("Login to Docker Hub for publishing image ...")
    try:
        subprocess.run(
            ["docker", "login", "-u", docker_username, "-p", docker_password, "docker.io"],
            check=True,
            # Silence the warning of passing password on the command line. This is not a problem since we are using it on local machine.
            stderr=subprocess.DEVNULL,
        )
        click.echo("Successfully logged into Docker Hub")
    except subprocess.CalledProcessError:
        click.echo("Failed to login to Docker Hub")
        raise

    click.echo(f"Pushing Docker image {docker_username}/{image_name}:latest ...")
    subprocess.run(["docker", "push", f"{docker_username}/{image_name}:latest"], check=True)

    click.echo("Agent's Docker image published successfully to Docker Hub")


def _galadriel_deploy(image_name: str, docker_username: str, galadriel_api_key: str) -> Optional[str]:
    """Deploy agent to Galadriel platform."""

    env_vars = dict(dotenv_values(".agents.env"))

    docker_image = f"{docker_username}/{image_name}:latest"
    image_hash = _get_image_hash(docker_image)

    payload = {
        "name": image_name,
        "docker_image": docker_image,
        "docker_image_hash": image_hash,
        "env_vars": env_vars,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {galadriel_api_key}",
        "accept": "application/json",
    }
    response = requests.post(
        f"{API_BASE_URL}/agents/",
        json=payload,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
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
Request Body: {response.request.body!r}
"""
    click.echo(error_msg)
    return None


def _galadriel_update(image_name: str, docker_username: str, agent_id: str) -> bool:
    """Update agent on Galadriel platform."""

    if not os.path.exists(".agents.env"):
        raise click.ClickException("No .agents.env file found in current directory. Please create one.")

    env_vars = dict(dotenv_values(".agents.env"))

    load_dotenv(dotenv_path=Path(".") / ".env")
    api_key = os.getenv("GALADRIEL_API_KEY")
    if not api_key:
        raise click.ClickException("GALADRIEL_API_KEY not found in environment")

    docker_image = f"{docker_username}/{image_name}:latest"
    image_hash = _get_image_hash(docker_image)

    payload = {
        "name": image_name,
        "docker_image": docker_image,
        "docker_image_hash": image_hash,
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
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code == 200:
        return True

    error_msg = f"""
Failed to update agent:
Status Code: {response.status_code}
Response: {response.text}
Request URL: {response.request.url}
Request Headers: {dict(response.request.headers)}
Request Body: {response.request.body!r}
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
    sanitized_name = re.sub(r"\W+", "_", user_input)  # Replace non-alphanumeric characters with _
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

    # FIXME Disable this check for now
    # Check if the .agents.env file exists
    # if not os.path.exists(".agents.env"):
    #    raise click.ClickException(
    #        "No .agents.env file found in current directory. Please run this command under your project directory."
    #    )

    # Update the .agents.env file with the new wallet path
    _update_agent_env_file({"SOLANA_KEY_PATH": path})

    keypair = Keypair()
    private_key_json = keypair.to_json()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(private_key_json)

    return str(keypair.pubkey())


def _request_airdrop(pubkey: str) -> None:
    """Request an airdrop of 0.0001 SOL to the given Solana wallet."""

    url = f"{API_BASE_URL}/faucet/solana"
    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
        },
        json={"address": pubkey},
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code == 200:
        click.echo(f"Airdrop requested successfully! Transaction hash: {response.json()['transaction_signature']}")
    elif response.status_code == 429:
        click.echo(f"Rate limit exceeded: {response.headers['error']}")
    else:
        click.echo(f"Failed to request airdrop: {response.status_code} {response.text}")


def _get_installed_galadriel_version() -> str:
    """
    Get the installed galadriel package version.

    Returns:
        The version string (e.g., "0.0.11")
    """
    try:
        import importlib.metadata

        return importlib.metadata.version("galadriel")
    except Exception as e:
        click.echo(f"Failed to get installed galadriel version: {e}")
        click.echo("Falling back to default version 0.0.11")
        return "0.0.11"
