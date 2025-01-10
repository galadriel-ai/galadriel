from galadriel_agent.responses import format_response


def test_success():
    assert "response" is format_response.execute("response")


def test_empty():
    assert None is format_response.execute("")


def test_contains_url():
    assert None is format_response.execute("response x.com")
    assert None is format_response.execute("response example.com")
    assert None is format_response.execute("response www.example.com")
    assert None is format_response.execute("response https://www.example.com")
    assert None is format_response.execute("response http://www.example.com")


def test_some_text():
    text = "This is an LLM response. Cool! Some sentence."
    assert text == format_response.execute(text)
    text = "This is an LLM response.\n\nCool!\nSome sentence.\nAsd"
    assert text == format_response.execute(text)
