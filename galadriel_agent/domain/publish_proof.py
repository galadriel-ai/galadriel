import json
import os
from typing import Dict
from typing import Optional

import requests

from galadriel_agent.logging_utils import get_agent_logger

logger = get_agent_logger()


def execute(request: Dict, response: Dict, hashed_data: str) -> bool:
    # TODO: url = "https://api.galadriel.com/v1/verified/chat/log"
    url = "http://localhost:5000/v1/verified/chat/log"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": _get_authorization(),
    }
    data = {
        "attestation": "TODO:",  # TODO
        "hash": hashed_data,
        "public_key": "TODO:",  # TODO
        "request": request,
        "response": response,
        "signature": "TODO:",  # TODO
    }
    try:
        result = requests.post(url, headers=headers, data=json.dumps(data))
        if result.status_code == 200:
            return True
    except:
        pass
    return False


def _get_authorization() -> Optional[str]:
    api_key = os.getenv("GALADRIEL_API_KEY")
    if api_key:
        return "Bearer " + api_key
    logger.info("GALADRIEL_API_KEY missing, set this as export GALADRIEL_API_KEY=<key>")
