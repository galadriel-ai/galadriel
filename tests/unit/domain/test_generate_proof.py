from galadriel.domain import generate_proof
from galadriel.entities import Message


def test_none():
    result = generate_proof.execute(None, None)
    assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_empty():
    result = generate_proof.execute(Message(id="test-id-1", content=""), Message(id="test-id-2", content=""))
    assert result == "52ababcd2769bb476088ff9341f479f29f0c481ca693b7122cf38ac9419f4fcc"


def test_hello_world():
    result = generate_proof.execute(
        Message(id="test-id-1", content="hello"),
        Message(id="test-id-2", content="world"),
    )
    assert result == "c38a220184ffa2508ef7ac3feb8a4a6cca63ef24527ff27e77f36a93c979ba2e"
