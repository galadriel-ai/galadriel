from galadriel_agent.domain import generate_proof


def test_none():
    result = generate_proof.execute(None, None)
    assert result == "2c7bddafa6f824cb0e682091aa1d9ca392883cb1f5bcff95389adc9feae77fcd"


def test_empty():
    result = generate_proof.execute({}, {})
    assert result == "b51f08b698d88d8027a935d9db649774949f5fb41a0c559bfee6a9a13225c72d"


def test_hello_world():
    result = generate_proof.execute(
        {"hello": "world"},
        {"hello": "result"}
    )
    assert result == "a18b334640a39f0c821ccb26e339ee2451398085727f652315548b031c53ddc9"
