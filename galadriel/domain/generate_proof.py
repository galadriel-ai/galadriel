import hashlib
import json
import base64
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives import serialization
from logging import Logger
from galadriel.entities import Message, Proof


async def generate_proof(request: Message, response: Message, logger: Logger) -> Proof:
    logger.info(f"request: {request} \nresponse: {response}")
    try:
        # get private key and public key
        private_key_pem = os.getenv("PRIVATE_KEY")
        public_key_pem = os.getenv("PUBLIC_KEY")
        if not private_key_pem or not public_key_pem:
            logger.error("PRIVATE_KEY or PUBLIC_KEY not set")
            raise ValueError("PRIVATE_KEY or PUBLIC_KEY not set")
        
        # Convert the string to bytes and load the private key
        private_key = serialization.load_ssh_private_key(
            data=private_key_pem.encode("utf-8"),
            password=None
        )
        public_key = serialization.load_ssh_public_key(
            data=public_key_pem.encode("utf-8")
        )
        
        # Hash data
        hashed_data = _hash_data(request, response)

        # Sign data directly using the private key
        signature = private_key.sign(hashed_data)

        # TODO: get attestation

        proof = Proof(
            hash=hashed_data.hex(),
            signature=signature.hex(),
            public_key=public_key,
            attestation="TODO",
        )
    except Exception as e:
        logger.error(f"Error generating proof: {e}")
        raise e

    return proof


def _hash_data(request: Message, response: Message) -> bytes:
    combined_str = f"{json.dumps(request.model_dump(), sort_keys=True)}{json.dumps(response.model_dump(), sort_keys=True)}"
    return hashlib.sha256(combined_str.encode("utf-8")).digest()


if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    from galadriel.logging_utils import get_agent_logger
    import asyncio

    def get_ssh_public_key(name: str) -> str:
        """Read the SSH public key from the default location."""
        try:
            ssh_path = Path.home() / ".ssh" / name
            if not ssh_path.exists():
                raise FileNotFoundError(f"SSH public key not found at {ssh_path}")
                
            with open(ssh_path, "r", encoding="utf-8") as f:
                return f.read().strip()
                
        except Exception as e:
            raise RuntimeError(f"Failed to read SSH public key: {e}") from e


    def set_ssh_key_env() -> None:
        """Set the SSH public key as an environment variable."""
        try:
            public_key = get_ssh_public_key("id_ed25519.pub")
            private_key = get_ssh_public_key("id_ed25519")
            os.environ["s_PUBLIC_KEY"] = public_key
            os.environ["s_PRIVATE_KEY"] = private_key
        except Exception as e:
            raise RuntimeError(f"Failed to set SSH public key environment variable: {e}") from e
        

    logger = get_agent_logger()
    load_dotenv(dotenv_path=Path(".") / ".env", override=True)
    #set_ssh_key_env()
    
    request = Message(content="Hello, world!")
    response = Message(content="Hello, world!")

    async def main():
        proof = await generate_proof(request, response, logger)
        print(proof)

    asyncio.run(main())

message = Message(additional_kwargs={"discord": "channel_id_123",
                                        "twitter": "tweet_id_456"})
## discord client - send message
if not message.additional_kwargs.get("discord"):
    "not for discord"
## twitter client - send message
if not message.additional_kwargs.get("twitter"):
    "not for twitter"
    
    
