import pytest
from smolagents import ActionStep, ToolCall
from galadriel.domain.extract_step_logs import pull_messages_from_step


@pytest.fixture
def basic_step():
    return ActionStep(
        step_number=1,
        model_output="This is a thought",
        duration=2.5,
        # Remove token counts as they're not part of ActionStep
    )


@pytest.fixture
def tool_call_step():
    tool_call = ToolCall(name="python_interpreter", arguments="print('hello')", id="123")
    return ActionStep(
        step_number=2,
        model_output="Let's run some code",
        tool_calls=[tool_call],
        observations="hello\n",
        duration=1.5,
    )


@pytest.mark.asyncio
async def test_basic_step():
    step = ActionStep(
        step_number=1,
        model_output="This is a thought",
        duration=1.0,  # Add duration to avoid None
        start_time=0,  # Add start_time
        end_time=1.0,  # Add end_time
    )
    messages = [msg async for msg in pull_messages_from_step(step, show_token_counts=True)]

    assert len(messages) == 3  # Step number, thought, summary
    assert messages[0].content == "\n**Step 1** \n"
    assert messages[1].content == "\nThis is a thought\n"
    assert "Duration: 1.0" in messages[2].content  # Summary


@pytest.mark.asyncio
async def test_python_tool_call():
    tool_call = ToolCall(name="python_interpreter", arguments="print('hello')", id="123")
    step = ActionStep(
        step_number=1,
        tool_calls=[tool_call],
        observations="hello\n",
        duration=1.0,
        start_time=0,
        end_time=1.0,
    )

    # Test with show_tool_code and show_execution_logs enabled
    messages = [msg async for msg in pull_messages_from_step(step, show_tool_code=True, show_execution_logs=True)]

    # Check for tool call (code block)
    code_blocks = [msg for msg in messages if isinstance(msg.content, str) and "```python" in msg.content]
    assert len(code_blocks) > 0

    # Check for tool output
    tool_outputs = [
        msg
        for msg in messages
        if isinstance(msg.content, str) and "Tool Output:" in msg.content and "hello" in msg.content
    ]
    assert len(tool_outputs) > 0


@pytest.mark.asyncio
async def test_error_handling():
    step = ActionStep(
        step_number=1,
        error="Test error",
        duration=1.0,
        start_time=0,
        end_time=1.0,
    )
    # Test with show_step_errors enabled
    messages = [msg async for msg in pull_messages_from_step(step, show_step_errors=True)]

    # Look for error message in content
    error_messages = [msg for msg in messages if isinstance(msg.content, str) and "Test error" in msg.content]
    assert len(error_messages) > 0

    # Test with show_step_errors disabled (default)
    messages = [msg async for msg in pull_messages_from_step(step)]
    error_messages = [msg for msg in messages if isinstance(msg.content, str) and "Test error" in msg.content]
    assert len(error_messages) == 0


@pytest.mark.asyncio
async def test_step_summary():
    step = ActionStep(
        step_number=1,
        duration=1.5,
        start_time=0,
        end_time=1.5,
    )
    # Test with show_token_counts enabled
    messages = [msg async for msg in pull_messages_from_step(step, show_token_counts=True)]

    # Look for duration in any message content
    summary_messages = [msg for msg in messages if isinstance(msg.content, str) and "Duration: 1.5" in msg.content]
    assert len(summary_messages) > 0

    # Test with show_token_counts disabled (default)
    messages = [msg async for msg in pull_messages_from_step(step)]
    summary_messages = [msg for msg in messages if isinstance(msg.content, str) and "Duration:" in msg.content]
    assert len(summary_messages) == 0


@pytest.mark.asyncio
async def test_code_in_thinking():
    step = ActionStep(
        step_number=1,
        model_output="Let's use this code:\n```python\nprint('hello')\n```\nto solve the problem.",
        duration=1.0,
        start_time=0,
        end_time=1.0,
    )

    # Test with show_code_in_thinking=True
    messages = [msg async for msg in pull_messages_from_step(step, show_code_in_thinking=True)]
    thinking_message = next((msg for msg in messages if msg.additional_kwargs.get("type") == "thinking"), None)
    assert thinking_message is not None
    assert "```python" in thinking_message.content

    # Test with show_code_in_thinking=False (default)
    messages = [msg async for msg in pull_messages_from_step(step)]
    thinking_message = next((msg for msg in messages if msg.additional_kwargs.get("type") == "thinking"), None)
    assert thinking_message is not None
    assert "```python" not in thinking_message.content


@pytest.mark.asyncio
async def test_tool_error_handling():
    tool_call = ToolCall(name="python_interpreter", arguments="print('hello')", id="123")
    step = ActionStep(
        step_number=1,
        tool_calls=[tool_call],
        error="Tool execution error",
        duration=1.0,
        start_time=0,
        end_time=1.0,
    )

    # Test with show_tool_errors enabled
    messages = [msg async for msg in pull_messages_from_step(step, show_tool_errors=True)]
    error_messages = [msg for msg in messages if isinstance(msg.content, str) and "Tool execution error" in msg.content]
    assert len(error_messages) > 0

    # Test with show_tool_errors disabled (default)
    messages = [msg async for msg in pull_messages_from_step(step)]
    error_messages = [msg for msg in messages if isinstance(msg.content, str) and "Tool execution error" in msg.content]
    assert len(error_messages) == 0
