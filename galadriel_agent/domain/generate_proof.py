import hashlib
import json
import base64
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from galadriel_agent.entities import Message, Proof
from galadriel_agent.logging_utils import get_agent_logger

logger = get_agent_logger()


def execute(request: Message, response: Message) -> Proof:
    logger.info(f"request: {request} \nresponse: {response}")
    try:
        # get private key and public key
        private_key = base64.b64decode(os.getenv("PRIVATE_KEY"))
        public_key = base64.b64decode(os.getenv("PUBLIC_KEY"))
        if not private_key or not public_key:
            logger.error("PRIVATE_KEY or PUBLIC_KEY not set")
            raise ValueError("PRIVATE_KEY or PUBLIC_KEY not set")
        
        # hash data
        hashed_data = _hash_data(request, response)

        # sign data
        private_key = Ed25519PrivateKey.from_private_bytes(private_key)
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
