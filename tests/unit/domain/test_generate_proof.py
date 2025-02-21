from galadriel.domain import generate_proof
from galadriel.entities import Message


def test_none():
    result = generate_proof.execute(None, None)
    assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_empty():
    result = generate_proof.execute(Message(id="test-id-1", content=""), Message(id="test-id-2", content=""))
    assert result == "f62856b4343d1e85f557c6843bbdd41b6d83e477862933373c04bd0aa12953c4"


def test_hello_world():
    result = generate_proof.execute(
        Message(id="test-id-1", content="hello"),
        Message(id="test-id-2", content="world"),
    )
    assert result == "b052ad007dd915ae19a56936c2d3aacf8ed19db3d155d7563a2eda5be3953c04"
