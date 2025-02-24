import pytest
from unittest.mock import MagicMock

from galadriel.domain.agent_state import upload_agent_state
from galadriel.entities import AgentState
from galadriel.errors import AgentStateError
from galadriel.repository.agent_state_repository import AgentStateRepository


@pytest.fixture
def mock_repository():
    return MagicMock(spec=AgentStateRepository)


@pytest.fixture
def sample_agent_state():
    return AgentState(agent_id="test_agent_123", type="TestAgentType", steps=[{"system_prompt": "Test prompt"}])


def test_upload_agent_state_success(mock_repository, sample_agent_state):
    """Test successful upload of agent state"""
    # Setup
    expected_key = "generated_key_123"
    mock_repository.upload_agent_state.return_value = expected_key

    # Execute
    result = upload_agent_state.execute(mock_repository, sample_agent_state, key=None)

    # Assert
    assert result == expected_key
    mock_repository.upload_agent_state.assert_called_once_with(sample_agent_state, None)


def test_upload_agent_state_with_key(mock_repository, sample_agent_state):
    """Test uploading agent state with a specific key"""
    # Setup
    input_key = "specific_key_456"
    mock_repository.upload_agent_state.return_value = input_key

    # Execute
    result = upload_agent_state.execute(mock_repository, sample_agent_state, key=input_key)

    # Assert
    assert result == input_key
    mock_repository.upload_agent_state.assert_called_once_with(sample_agent_state, input_key)


def test_upload_agent_state_failure(mock_repository, sample_agent_state):
    """Test handling of upload failure when repository returns None"""
    # Setup
    mock_repository.upload_agent_state.return_value = None

    # Execute and Assert
    with pytest.raises(AgentStateError, match="Failed to upload agent state"):
        upload_agent_state.execute(mock_repository, sample_agent_state, key=None)

    mock_repository.upload_agent_state.assert_called_once_with(sample_agent_state, None)
