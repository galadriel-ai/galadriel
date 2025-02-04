from galadriel.domain import generate_proof
from galadriel.entities import Message


def test_none():
    result = generate_proof.execute(None, None)
    assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_empty():
    result = generate_proof.execute(Message(content=""), Message(content=""))
    assert result == "48b31d5a4b8d609632cef2b1ad68e0e8dd1c56b6f7fd0888d4e1e11263185e0e"


def test_hello_world():
    result = generate_proof.execute(
        Message(content="hello"),
        Message(content="world"),
    )
    assert result == "9041cb20b1ab3c83a4945cbab0c651d3e8eb1fd0a2239203a331a7ad2a5be4f0"
