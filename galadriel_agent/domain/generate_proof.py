import hashlib
import json
from typing import Dict


def execute(request: Dict, response: Dict) -> str:
    return _hash_data(request, response)


def _hash_data(request: Dict, response: Dict) -> str:
    combined_str = f"{_dump(request)}{_dump(response)}"
    return hashlib.sha256(combined_str.encode("utf-8")).digest().hex()


def _dump(data: Dict) -> str:
    return json.dumps(data, sort_keys=True)
