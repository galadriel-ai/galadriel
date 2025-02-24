import pytest
from unittest.mock import MagicMock

from galadriel.core_agent import (
    MultiStepAgent,
    SystemPromptStep,
    TaskStep,
    ActionStep,
    PlanningStep,
)
from galadriel.domain.agent_state import restore_agent_state
from galadriel.entities import AgentState


def test_restore_agent_state_with_valid_state():
    """Test restoring agent state with valid data"""
    # Setup
    agent_id = "test_agent_123"
    mock_agent = MagicMock(spec=MultiStepAgent)
    mock_agent.agent_id = agent_id

    # Create test steps
    system_prompt_step = SystemPromptStep(system_prompt="I am a test system prompt")
    task_step = TaskStep(task="Sample task")

    # Create agent state
    agent_state = AgentState(
        agent_id=agent_id,
        type=str(type(mock_agent)),
        steps=[
            system_prompt_step.dict(),
            task_step.dict(),
        ],
    )

    # Execute
    restore_agent_state.execute(mock_agent, agent_state)

    # Assert
    assert mock_agent.memory.system_prompt.system_prompt == system_prompt_step.system_prompt
    assert len(mock_agent.memory.steps) == 1
    assert isinstance(mock_agent.memory.steps[0], TaskStep)
    assert mock_agent.memory.steps[0].task == task_step.task


def test_restore_different_step_types():
    """Test restoring different types of memory steps"""
    agent_id = "test_agent_123"
    mock_agent = MagicMock(spec=MultiStepAgent)
    mock_agent.agent_id = agent_id

    # Create different types of steps
    system_prompt_step = SystemPromptStep(system_prompt="Test system prompt")
    action_step = ActionStep(
        tool_calls=[],
    )
    planning_step = PlanningStep(
        facts=["fact1", "fact2"],
        plan=["step1", "step2"],
        model_input_messages="",
        model_output_message_facts="",
        model_output_message_plan="",
    )
    task_step = TaskStep(task="Sample task")

    agent_state = AgentState(
        agent_id=agent_id,
        type=str(type(mock_agent)),
        steps=[
            system_prompt_step.dict(),
            action_step.dict(),
            planning_step.dict(),
            task_step.dict(),
        ],
    )

    print(action_step.dict())
    # Execute
    restore_agent_state.execute(mock_agent, agent_state)

    # Assert
    assert mock_agent.memory.system_prompt.system_prompt == system_prompt_step.system_prompt
    assert len(mock_agent.memory.steps) == 3
    assert isinstance(mock_agent.memory.steps[0], ActionStep)
    assert isinstance(mock_agent.memory.steps[1], PlanningStep)
    assert isinstance(mock_agent.memory.steps[2], TaskStep)


def test_restore_agent_state_mismatched_agent_id():
    """Test that restoration fails when agent IDs don't match"""
    mock_agent = MagicMock(spec=MultiStepAgent)
    mock_agent.agent_id = "agent_123"

    system_prompt_step = SystemPromptStep(system_prompt="Test system prompt")
    agent_state = AgentState(
        agent_id="different_agent_id", type=str(type(mock_agent)), steps=[system_prompt_step.dict()]
    )

    with pytest.raises(AssertionError, match="Agent ID in AgentState does not match"):
        restore_agent_state.execute(mock_agent, agent_state)


def test_restore_agent_state_mismatched_type():
    """Test that restoration fails when agent types don't match"""
    agent_id = "test_agent_123"
    mock_agent = MagicMock(spec=MultiStepAgent)
    mock_agent.agent_id = agent_id

    system_prompt_step = SystemPromptStep(system_prompt="Test system prompt")
    agent_state = AgentState(agent_id=agent_id, type="DifferentAgentType", steps=[system_prompt_step.dict()])

    with pytest.raises(AssertionError, match="Agent type in AgentState does not match"):
        restore_agent_state.execute(mock_agent, agent_state)


def test_restore_agent_state_missing_system_prompt():
    """Test that restoration fails when system prompt is missing"""
    agent_id = "test_agent_123"
    mock_agent = MagicMock(spec=MultiStepAgent)
    mock_agent.agent_id = agent_id

    task_step = TaskStep(task="Sample task")
    agent_state = AgentState(agent_id=agent_id, type=str(type(mock_agent)), steps=[task_step.dict()])

    with pytest.raises(AssertionError, match="SystemPromptStep is required"):
        restore_agent_state.execute(mock_agent, agent_state)


def test_restore_memory_step_unknown_type():
    """Test that restoration fails with unknown memory step type"""
    unknown_step_data = {"unknown_field": "some_value"}

    with pytest.raises(ValueError, match="Unknown MemoryStep type"):
        restore_agent_state._restore_memory_step(unknown_step_data)
