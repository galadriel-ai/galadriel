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


    
    
