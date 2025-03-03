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
    messages = [msg async for msg in pull_messages_from_step(step)]

    assert len(messages) == 4  # Step number, thought, summary, separator
    assert messages[0].content == "**Step 1**"
    assert messages[1].content == "This is a thought"
    assert "Step 1" in messages[2].content  # Summary
    assert messages[3].content == "-----\n```\n"  # Separator


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

    messages = [msg async for msg in pull_messages_from_step(step)]
    code_blocks = [msg for msg in messages if isinstance(msg.content, str) and "```python" in msg.content]
    assert len(code_blocks) > 0
    # Look for tool output in any message
    tool_outputs = [msg for msg in messages if isinstance(msg.content, str) and "hello" in msg.content]
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
    messages = [msg async for msg in pull_messages_from_step(step)]

    # Look for error message in content
    error_messages = [msg for msg in messages if isinstance(msg.content, str) and "Test error" in msg.content]
    assert len(error_messages) > 0


@pytest.mark.asyncio
async def test_step_summary():
    step = ActionStep(
        step_number=1,
        duration=1.5,
        start_time=0,
        end_time=1.5,
    )
    messages = [msg async for msg in pull_messages_from_step(step)]

    # Look for duration in any message content
    summary_messages = [msg for msg in messages if isinstance(msg.content, str) and "Duration: 1.5" in msg.content]
    assert len(summary_messages) > 0


@pytest.mark.asyncio
async def test_conversation_id_propagation():
    step = ActionStep(
        step_number=1,
        model_output="Test",
        duration=1.0,
        start_time=0,
        end_time=1.0,
    )
    conv_id = "test-conversation"
    messages = [msg async for msg in pull_messages_from_step(step, conversation_id=conv_id)]

    assert all(msg.conversation_id == conv_id for msg in messages)


@pytest.mark.asyncio
async def test_additional_kwargs_propagation():
    step = ActionStep(
        step_number=1,
        model_output="Test",
        duration=1.0,
        start_time=0,
        end_time=1.0,
    )
    additional_kwargs = {"test_key": "test_value"}
    messages = [msg async for msg in pull_messages_from_step(step, additional_kwargs=additional_kwargs)]

    assert all("test_key" in msg.additional_kwargs for msg in messages)
    assert all(msg.additional_kwargs["test_key"] == "test_value" for msg in messages)


@pytest.mark.asyncio
async def test_non_action_step():
    """Test that non-ActionStep objects return no messages"""
    messages = [msg async for msg in pull_messages_from_step("not a step")]
    assert len(messages) == 0
