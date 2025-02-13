import json
import os

import boto3
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Optional
from botocore.exceptions import ClientError

from galadriel_agent.logging_utils import get_agent_logger
from galadriel.entities import AgentState

logger = get_agent_logger()


class S3Repository:
    def __init__(self, bucket_name: str):
        """Initialize S3 client with bucket name.

        Args:
            bucket_name: Name of the S3 bucket to use
        """
        self.s3_client = boto3.client("s3")
        self.bucket_name = bucket_name

    def download_agent_state(
        self, agent_id: str, key: Optional[str] = None
    ) -> Optional[AgentState]:
        """Download agent state from S3. If key is None, the latest version will be fetched.

        Args:
            agent_id: The identifier of the agent.
            key: (Optional) The key to use for the downloaded file. If None, the latest version will be fetched.

        Returns:
            JSON string if successful, None if failed.
        """
        try:
            # Determine the correct S3 key
            if key:
                download_key = f"agents/{agent_id}/{key}.json"
            else:
                download_key = f"agents/{agent_id}/latest.json"  # Fetch latest version

            # Fetch the file from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=download_key
            )

            # Read and return JSON content as a string
            json_str = response["Body"].read().decode("utf-8")
            return AgentState.parse_raw(json_str)
        except ClientError as e:
            logger.error(f"Failed to download JSON from S3: {str(e)}")
            return None

    def upload_agent_state(
        self, state: AgentState, key: Optional[str] = None
    ) -> Optional[str]:
        """Upload agent state as JSON to S3.

        Args:
            state: The agent's state.
            key: The key to use for the uploaded file. If None, a timestamp will be used and latest state version will be updated.

        Returns:
            The key used for the uploaded file, or None if the upload failed.
        """
        try:
            json_data = state.json()

            versioning = False
            if key:
                upload_key = f"agents/{state.agent_id}/{key}.json"  # Versioned file
            else:
                key = datetime.now().strftime("%Y%m%d_%H%M%S")
                upload_key = f"agents/{state.agent_id}/{key}.json"  # Versioned file
                versioning = True

            # Upload
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=upload_key,
                Body=json_data,
                ContentType="application/json",
            )

            # Upload (or overwrite) latest.json
            if versioning:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=f"agents/{state.agent_id}/latest.json",
                    Body=json_data,
                    ContentType="application/json",
                )
            return key

        except ClientError as e:
            logger.error(f"Failed to upload JSON to S3: {str(e)}")
            return None
