import os
import pytest
from unittest.mock import call, MagicMock, patch
from botocore.exceptions import ClientError

from galadriel.state.agent_state_repository import AgentStateRepository

AGENT_ID = "test-agent-123"
BUCKET_NAME = "agents-memory-storage"


@pytest.fixture
def mock_agent_id(monkeypatch):
    """Mock the AGENT_ID environment variable."""
    monkeypatch.setenv("AGENT_ID", AGENT_ID)
    yield AGENT_ID


@pytest.fixture
def mock_s3_client():
    with patch("boto3.client") as mock_boto3_client:
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def repository(mock_s3_client, mock_agent_id):
    return AgentStateRepository()


@patch.object(AgentStateRepository, "_download_folder_from_s3", return_value=True)
def test_download_with_specific_key(mock_download_folder, repository):
    """Test downloading agent state with a specific key"""
    key = "specific_key"

    result = repository.download_agent_state(key)

    assert result is not None
    mock_download_folder.assert_called_once_with(
        f"agents/{AGENT_ID}/{key}/",
        f"/tmp/{AGENT_ID}/{key}/",
    )


@patch.object(AgentStateRepository, "_download_folder_from_s3", return_value=True)
def test_download_latest(mock_download_folder, repository, mock_s3_client):
    """Test downloading latest agent state"""
    latest_key = "state_20240226"
    mock_s3_client.get_object.return_value = {"Body": MagicMock(read=lambda: latest_key.encode())}

    result = repository.download_agent_state()

    assert result is not None
    mock_s3_client.get_object.assert_called_once_with(Bucket=BUCKET_NAME, Key=f"agents/{AGENT_ID}/latest.state")
    mock_download_folder.assert_called_once_with(
        f"agents/{AGENT_ID}/{latest_key}/",
        f"/tmp/{AGENT_ID}/{latest_key}/",
    )


@patch.object(AgentStateRepository, "_download_folder_from_s3", return_value=True)
def test_download_client_error(mock_download_folder, repository, mock_s3_client):
    """Test handling of S3 client errors during download"""
    mock_s3_client.get_object.side_effect = ClientError(
        error_response={"Error": {"Code": "NoSuchKey"}}, operation_name="GetObject"
    )

    result = repository.download_agent_state()

    assert result is None
    mock_download_folder.assert_not_called()


@patch.object(AgentStateRepository, "_upload_folder_to_s3", return_value=True)
def test_upload_with_specific_key(mock_upload_folder, repository, mock_s3_client):
    """Test uploading agent state with a specific key"""
    file_path = "/tmp/test"
    key = "specific_key"

    result = repository.upload_agent_state(file_path, key)

    assert result == key
    mock_upload_folder.assert_called_once_with(file_path, f"agents/{AGENT_ID}/state_{key}")
    mock_s3_client.put_object.assert_called_once_with(
        Bucket=BUCKET_NAME,
        Key=f"agents/{AGENT_ID}/latest.state",
        Body=key.encode(),
    )


@patch.object(AgentStateRepository, "_upload_folder_to_s3", return_value=True)
def test_upload_without_key(mock_upload_folder, repository, mock_s3_client):
    """Test uploading agent state without a specific key"""
    file_path = "/tmp/test"

    with patch("galadriel.state.agent_state_repository.datetime") as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "20240226_150000"
        result = repository.upload_agent_state(file_path)

    assert result == "20240226_150000"
    mock_upload_folder.assert_called_once_with(file_path, f"agents/{AGENT_ID}/state_20240226_150000")
    mock_s3_client.put_object.assert_called_once_with(
        Bucket=BUCKET_NAME,
        Key=f"agents/{AGENT_ID}/latest.state",
        Body=b"20240226_150000",
    )


def test_upload_folder_to_s3(repository, mock_s3_client, tmp_path):
    """Test _upload_folder_to_s3 uploads all files while preserving structure"""

    # Create test directory and files
    local_folder = tmp_path / "test_upload"
    local_folder.mkdir()

    (local_folder / "file1.txt").write_text("content1")
    (local_folder / "subdir").mkdir()
    (local_folder / "subdir/file2.txt").write_text("content2")

    remote_folder = "agents/test-instance/state_20240226/"

    # Call the private method directly
    repository._upload_folder_to_s3(str(local_folder), remote_folder)

    # Expected S3 upload calls
    expected_calls = [
        call(
            str(local_folder / "file1.txt"),
            repository.bucket_name,
            f"{remote_folder}file1.txt",
        ),
        call(
            str(local_folder / "subdir/file2.txt"),
            repository.bucket_name,
            f"{remote_folder}subdir/file2.txt",
        ),
    ]

    # Assert that upload_file was called correctly
    mock_s3_client.upload_file.assert_has_calls(expected_calls, any_order=True)
    assert mock_s3_client.upload_file.call_count == 2


def test_download_folder_from_s3(repository, mock_s3_client, tmp_path):
    """Test _download_folder_from_s3 downloads all files while preserving structure"""

    # Mock S3 response with multiple files
    mock_s3_client.get_paginator.return_value.paginate.return_value = [
        {
            "Contents": [
                {"Key": "agents/test-instance/state_20240226/file1.txt"},
                {"Key": "agents/test-instance/state_20240226/subdir/file2.txt"},
            ]
        }
    ]

    local_folder = tmp_path / "test_download"
    remote_folder = "agents/test-instance/state_20240226/"

    # Mock the download_file method
    def mock_download_file(bucket, s3_key, local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w") as f:
            f.write("mock_data")

    mock_s3_client.download_file.side_effect = mock_download_file

    # Call the private method
    success = repository._download_folder_from_s3(remote_folder, str(local_folder))

    # Assert function returned True
    assert success

    # Check if files were created locally
    assert (local_folder / "file1.txt").exists()
    assert (local_folder / "subdir/file2.txt").exists()

    # Verify S3 download calls
    mock_s3_client.download_file.assert_any_call(
        repository.bucket_name,
        "agents/test-instance/state_20240226/file1.txt",
        str(local_folder / "file1.txt"),
    )
    mock_s3_client.download_file.assert_any_call(
        repository.bucket_name,
        "agents/test-instance/state_20240226/subdir/file2.txt",
        str(local_folder / "subdir/file2.txt"),
    )
    assert mock_s3_client.download_file.call_count == 2
