import json
from unittest.mock import MagicMock

from galadriel_agent.domain import publish_proof


class MockResponse:
    status_code = 200


def setup_function():
    publish_proof.requests = MagicMock()
    publish_proof.requests.post.return_value = MockResponse()


def test_execute_success():
    request = {"hello": "request"}
    response = {"hello": "response"}
    hashed_data = "mock_hash"
    result = publish_proof.execute(request, response, hashed_data)
    assert result


def test_execute_error():
    mock_response = MockResponse()
    mock_response.status_code = 500
    publish_proof.requests.post.return_value = mock_response

    request = {"hello": "request"}
    response = {"hello": "response"}
    hashed_data = "mock_hash"
    result = publish_proof.execute(request, response, hashed_data)
    assert not result


def test_execute_calls_endpoint():
    request = {"hello": "request"}
    response = {"hello": "response"}
    hashed_data = "mock_hash"
    publish_proof.execute(request, response, hashed_data)

    publish_proof.requests.post.assert_called_with(
        "http://localhost:5000/v1/verified/chat/log",
        headers={
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": None,
        },
        data=json.dumps(
            {
                "attestation": "TODO:",
                "hash": hashed_data,
                "public_key": "TODO:",
                "request": request,
                "response": response,
                "signature": "TODO:",
            }
        ),
    )
