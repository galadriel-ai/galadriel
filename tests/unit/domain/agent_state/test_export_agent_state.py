from unittest.mock import MagicMock

from galadriel.domain.agent_state import export_agent_state
from galadriel.core_agent import SystemPromptStep, TaskStep


def test_execute_exports_agent_state():
    """
    Test that execute correctly exports an agent's state including system prompt and steps
    """
    # Setup
    agent_id = "test_agent_123"

    # Create mock system prompt step
    system_prompt = SystemPromptStep(system_prompt="I am a test system prompt")
    task_step = TaskStep(
        task="What is 2+2?",
    )

    # Create mock agent
    mock_agent = MagicMock()
    mock_agent.memory = MagicMock()
    mock_agent.memory.system_prompt = system_prompt
    mock_agent.memory.steps = [task_step]

    # Execute
    result = export_agent_state.execute(agent_id=agent_id, agent=mock_agent)

    # Assert
    assert result.agent_id == agent_id
    assert result.type == str(type(mock_agent))
    assert len(result.steps) == 2  # system prompt + task step

    # Verify system prompt was exported correctly
    assert result.steps[0] == system_prompt.dict()

    # Verify steps were exported correctly
    assert result.steps[1] == task_step.dict()


def test_execute_with_empty_steps():
    """
    Test that execute works correctly with an agent that has no conversation steps
    """
    agent_id = "empty_agent"

    # Create mock system prompt
    system_prompt = SystemPromptStep(system_prompt="Test system prompt")

    # Create mock agent with no steps
    mock_agent = MagicMock()
    mock_agent.memory = MagicMock()
    mock_agent.memory.system_prompt = system_prompt
    mock_agent.memory.steps = []

    # Execute
    result = export_agent_state.execute(agent_id=agent_id, agent=mock_agent)

    # Assert
    assert result.agent_id == agent_id
    assert result.type == str(type(mock_agent))
    assert len(result.steps) == 1  # only system prompt
    assert result.steps[0] == system_prompt.dict()


def test_execute_preserves_step_order():
    """
    Test that execute preserves the order of steps in the agent's memory
    """
    agent_id = "order_test_agent"

    # Create mock system prompt and steps
    system_prompt = SystemPromptStep(system_prompt="Test system prompt")
    steps = [
        TaskStep(
            task=f"Task {i}",
            task_images=None
        )
        for i in range(5)
    ]

    # Create mock agent
    mock_agent = MagicMock()
    mock_agent.memory = MagicMock()
    mock_agent.memory.system_prompt = system_prompt
    mock_agent.memory.steps = steps

    # Execute
    result = export_agent_state.execute(agent_id=agent_id, agent=mock_agent)

    # Assert steps are in correct order
    for i, step in enumerate(steps):
        # Add 1 to index because system prompt is first
        assert result.steps[i + 1] == step.dict()
