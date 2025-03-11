import base64
import hashlib
import json
import os
from urllib.parse import urljoin
from typing import Optional

import requests
from cryptography.hazmat.primitives import serialization

from galadriel.entities import GALADRIEL_API_BASE_URL, Message, Proof
from galadriel.docker.galadriel_base_image.enclave_services.nsm_util import NSMUtil

PRIVATE_KEY_PATH = "/private_key.pem"
PUBLIC_KEY_PATH = "/public_key.pem"


class Prover:
    def __init__(self):
        self.authorization = self._get_authorization()
        if self.authorization is None:
            raise ValueError("GALADRIEL_API_KEY is not set")
        with open(PRIVATE_KEY_PATH, "rb") as priv_file:
            self.private_key = serialization.load_pem_private_key(data=priv_file.read(), password=None)

        with open(PUBLIC_KEY_PATH, "rb") as pub_file:
            self.public_key = serialization.load_pem_public_key(data=pub_file.read())
            self.public_key_bytes = self.public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        self.nsm_util = NSMUtil()

    async def generate_proof(self, request: Message, response: Message) -> Proof:
        try:
            # Hash data
            hashed_data = self._hash_data(request, response)

            # Sign data directly using the private key
            signature = self.sign(hashed_data)

            # Get attestation doc
            attestation_doc = self.nsm_util.get_attestation_doc(self.public_key_bytes)

            proof = Proof(
                hash=hashed_data.hex(),
                signature=signature.hex(),
                public_key=self.public_key_bytes.hex(),
                attestation=base64.b64encode(attestation_doc).decode(),
            )
        except Exception as e:
            raise e

        return proof

    def sign(self, data: bytes) -> bytes:
        return self.private_key.sign(data)

    def _hash_data(self, request: Message, response: Message) -> bytes:
        combined_str = (
            f"{json.dumps(request.model_dump(), sort_keys=True)}{json.dumps(response.model_dump(), sort_keys=True)}"
        )
        return self.hash(combined_str)

    def hash(self, value: str) -> bytes:
        return hashlib.sha256(value.encode("utf-8")).digest()

    async def publish_proof(self, request: Message, response: Message, proof: Proof) -> bool:
        url = urljoin(GALADRIEL_API_BASE_URL, "/verified/chat/log")
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": self.authorization,
        }
        data = {
            "attestation": proof.attestation,
            "hash": proof.hash,
            "public_key": proof.public_key,
            "request": request.model_dump(),
            "response": response.model_dump(),
            "signature": proof.signature,
        }
        try:
            result = requests.post(url, headers=headers, data=json.dumps(data))
            if result.status_code == 200:
                return True
        except Exception:
            pass
        return False

    def _get_authorization(self) -> Optional[str]:
        api_key = os.getenv("GALADRIEL_API_KEY")
        if api_key:
            return "Bearer " + api_key
        return None
