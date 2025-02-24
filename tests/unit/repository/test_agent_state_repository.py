import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from galadriel.repository.agent_state_repository import AgentStateRepository
from galadriel.entities import AgentState


@pytest.fixture
def mock_s3_client():
    with patch("boto3.client") as mock_boto3_client:
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def repository(mock_s3_client):
    return AgentStateRepository(bucket_name="test-bucket")


@pytest.fixture
def sample_agent_state():
    return AgentState(agent_id="test_agent_123", type="TestAgentType", steps=[{"system_prompt": "Test prompt"}])


def test_download_with_specific_key(repository, mock_s3_client):
    """Test downloading agent state with a specific key"""
    # Setup
    agent_id = "test_agent"
    key = "specific_key"
    expected_state = AgentState(agent_id=agent_id, type="TestType", steps=[{"system_prompt": "Test"}])

    # Mock S3 response
    mock_s3_client.get_object.return_value = {"Body": MagicMock(read=lambda: expected_state.json().encode())}

    # Execute
    result = repository.download_agent_state(agent_id, key)

    # Assert
    assert result == expected_state
    mock_s3_client.get_object.assert_called_once_with(Bucket="test-bucket", Key=f"agents/{agent_id}/{key}.json")


def test_download_latest(repository, mock_s3_client):
    """Test downloading latest agent state"""
    # Setup
    agent_id = "test_agent"
    expected_state = AgentState(agent_id=agent_id, type="TestType", steps=[{"system_prompt": "Test"}])

    # Mock S3 response
    mock_s3_client.get_object.return_value = {"Body": MagicMock(read=lambda: expected_state.json().encode())}

    # Execute
    result = repository.download_agent_state(agent_id)

    # Assert
    assert result == expected_state
    mock_s3_client.get_object.assert_called_once_with(Bucket="test-bucket", Key=f"agents/{agent_id}/latest.json")


def test_download_client_error(repository, mock_s3_client):
    """Test handling of S3 client errors during download"""
    # Setup
    mock_s3_client.get_object.side_effect = ClientError(
        error_response={"Error": {"Code": "NoSuchKey"}}, operation_name="GetObject"
    )

    # Execute
    result = repository.download_agent_state("test_agent")

    # Assert
    assert result is None


def test_upload_with_specific_key(repository, mock_s3_client, sample_agent_state):
    """Test uploading agent state with a specific key"""
    # Setup
    key = "specific_key"

    # Execute
    result = repository.upload_agent_state(sample_agent_state, key)

    # Assert
    assert result == key
    mock_s3_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=f"agents/{sample_agent_state.agent_id}/{key}.json",
        Body=sample_agent_state.json(),
        ContentType="application/json",
    )


def test_upload_without_key(repository, mock_s3_client, sample_agent_state):
    """Test uploading agent state without a specific key"""
    # Execute
    result = repository.upload_agent_state(sample_agent_state)

    # Assert
    assert result is not None  # Should return a generated timestamp key

    # Should have been called twice - once for versioned file and once for latest
    assert mock_s3_client.put_object.call_count == 2

    # Verify the calls
    calls = mock_s3_client.put_object.call_args_list
    assert all(call.kwargs["Body"] == sample_agent_state.json() for call in calls)
    assert all(call.kwargs["Bucket"] == "test-bucket" for call in calls)
    assert any("latest.json" in call.kwargs["Key"] for call in calls)


def test_upload_client_error(repository, mock_s3_client, sample_agent_state):
    """Test handling of S3 client errors during upload"""
    # Setup
    mock_s3_client.put_object.side_effect = ClientError(
        error_response={"Error": {"Code": "InvalidRequest"}}, operation_name="PutObject"
    )

    # Execute
    result = repository.upload_agent_state(sample_agent_state)

    # Assert
    assert result is None
