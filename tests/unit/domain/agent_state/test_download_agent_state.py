import pytest
from unittest.mock import MagicMock

from galadriel.domain.agent_state import download_agent_state
from galadriel.entities import AgentState
from galadriel.errors import AgentStateError
from galadriel.repository.agent_state_repository import AgentStateRepository


@pytest.fixture
def mock_repository():
    return MagicMock(spec=AgentStateRepository)


def test_download_agent_state_success(mock_repository):
    """Test successful download of agent state"""
    # Setup
    agent_id = "test_agent_123"
    key = "test_key"
    expected_state = AgentState(agent_id=agent_id, type="TestAgentType", steps=[{"system_prompt": "Test prompt"}])

    # Configure mock to return expected state
    mock_repository.download_agent_state.return_value = expected_state

    # Execute
    result = download_agent_state.execute(mock_repository, agent_id, key)

    # Assert
    assert result == expected_state
    mock_repository.download_agent_state.assert_called_once_with(agent_id, key)


def test_download_agent_state_with_no_key(mock_repository):
    """Test downloading agent state without providing a key"""
    # Setup
    agent_id = "test_agent_123"
    expected_state = AgentState(agent_id=agent_id, type="TestAgentType", steps=[{"system_prompt": "Test prompt"}])

    # Configure mock
    mock_repository.download_agent_state.return_value = expected_state

    # Execute
    result = download_agent_state.execute(mock_repository, agent_id, None)

    # Assert
    assert result == expected_state
    mock_repository.download_agent_state.assert_called_once_with(agent_id, None)


def test_download_agent_state_failure(mock_repository):
    """Test handling of download failure when repository returns None"""
    # Setup
    agent_id = "test_agent_123"
    key = "test_key"

    # Configure mock to return None (simulating failure)
    mock_repository.download_agent_state.return_value = None

    # Execute and Assert
    with pytest.raises(AgentStateError, match="Failed to download agent state"):
        download_agent_state.execute(mock_repository, agent_id, key)

    mock_repository.download_agent_state.assert_called_once_with(agent_id, key)
