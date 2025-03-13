import os
import boto3
from datetime import datetime
from typing import Optional
from botocore.exceptions import ClientError

from galadriel.entities import AgentState
from galadriel.logging_utils import get_agent_logger

logger = get_agent_logger()


class AgentStateRepository:
    def __init__(self):
        self.agent_id = os.getenv("AGENT_ID")
        self.s3_client = boto3.client("s3")
        self.bucket_name = "agents-memory-storage"

    def download_agent_state(self, key: Optional[str] = None) -> Optional[AgentState]:
        """Download agent state folder from S3 to a local temp directory.

        Args:
            key: (Optional) The key to use for the downloaded folder. If None, the latest version will be fetched.

        Returns:
            AgentState if successful, None if failed.
        """
        try:
            if key is None:
                # Fetch the latest state key from S3
                latest_marker_path = f"agents/{self.agent_id}/latest.state"
                key_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=latest_marker_path)
                key = key_obj["Body"].read().decode("utf-8")  # Read the state key from file

            remote_folder_path = f"agents/{self.agent_id}/{key}/"
            local_folder_path = f"/tmp/{self.agent_id}/{key}/"

            # Download the full folder
            success = self._download_folder_from_s3(remote_folder_path, local_folder_path)
            return AgentState(memory_folder_path=local_folder_path) if success else None

        except (ClientError, Exception) as e:
            logger.error(f"Failed to download agent state from S3: {str(e)}")
            return None

    def upload_agent_state(self, local_folder_path: str, key: Optional[str] = None) -> Optional[str]:
        """Upload agent state folder to S3.

        Args:
            local_folder_path: Path to the folder to upload.
            key: The key to use for the uploaded folder. If None, a timestamp will be used and latest state version will be updated.

        Returns:
            str: The key of the uploaded folder.
        """
        try:
            key = key or datetime.now().strftime("%Y%m%d_%H%M%S")
            remote_folder_path = f"agents/{self.agent_id}/state_{key}"

            # Upload folder to S3
            success = self._upload_folder_to_s3(local_folder_path, remote_folder_path)
            if success:
                # Update the "latest" reference
                latest_marker_path = f"agents/{self.agent_id}/latest.state"
                self.s3_client.put_object(Bucket=self.bucket_name, Key=latest_marker_path, Body=key.encode())
                return key
            return None
        except (ClientError, Exception) as e:
            logger.error(f"Failed to upload agent state to S3: {str(e)}")
            return None

    def _upload_folder_to_s3(self, local_folder: str, remote_folder: str) -> bool:
        """Upload a full folder to S3 while maintaining directory structure.

        Args:
            local_folder (str): The source folder on the local system.
            remote_folder (str): The destination folder in S3.
        """
        try:
            for root, _, files in os.walk(local_folder):
                for file in files:
                    local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, local_folder)
                s3_path = f"{remote_folder.rstrip('/')}/{relative_path}"
                self.s3_client.upload_file(local_path, self.bucket_name, s3_path)
            return True
        except ClientError as e:
            logger.error(f"Failed to upload folder to S3: {str(e)}")
            return False

    def _download_folder_from_s3(self, remote_folder_path: str, local_folder_path: str) -> bool:
        """Download a full folder from S3 while maintaining directory structure.

        Args:
            remote_folder_path (str): The folder path in S3.
            local_folder_path (str): The destination folder on the local system.

        Returns:
            bool: True if successful, False if an error occurs.
        """
        try:
            os.makedirs(local_folder_path, exist_ok=True)

            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=remote_folder_path):
                for obj in page.get("Contents", []):
                    s3_file_path = obj["Key"]
                    relative_path = os.path.relpath(s3_file_path, remote_folder_path)
                    local_file_path = os.path.join(local_folder_path, relative_path)

                    # Ensure local directories exist
                    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

                    # Download each file
                    self.s3_client.download_file(self.bucket_name, s3_file_path, local_file_path)

            return True
        except ClientError as e:
            logger.error(f"Failed to download folder from S3: {str(e)}")
            return False
