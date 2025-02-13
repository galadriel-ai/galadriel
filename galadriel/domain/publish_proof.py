import json
import os
from typing import Optional
from logging import Logger
import requests

from galadriel.entities import Message, Proof


async def publish_proof(request: Message, response: Message, proof: Proof, logger: Logger) -> bool:
    # TODO: url = "https://api.galadriel.com/v1/verified/chat/log"
    url = "http://localhost:5000/v1/verified/chat/log"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": _get_authorization(logger),
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


def _get_authorization(logger: Logger) -> Optional[str]:
    api_key = os.getenv("GALADRIEL_API_KEY")
    if api_key:
        return "Bearer " + api_key
    logger.info("GALADRIEL_API_KEY missing, set this as export GALADRIEL_API_KEY=<key>")
    return None
