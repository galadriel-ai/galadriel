from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from galadriel.logging_utils import get_agent_logger

logger = get_agent_logger()


class S3Client:
    def __init__(self, bucket_name: str):
        """Initialize S3 client with bucket name.

        Args:
            bucket_name: Name of the S3 bucket to use
        """
        self.s3_client = boto3.client("s3")
        self.bucket_name = bucket_name

    async def upload_file(self, file_path: str, agent_name: str) -> Optional[str]:
        """Upload a file to S3 with timestamp in name.

        Args:
            file_path: Local path of file to upload
            agent_name: Name of the agent uploading the file

        Returns:
            S3 path if successful, None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{agent_name}_{timestamp}"

            s3_path = f"agents/{agent_name}/{filename}.json"

            self.s3_client.upload_file(file_path, self.bucket_name, s3_path)
            logger.info(f"Successfully uploaded {file_path} to {s3_path}")
            return s3_path

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {str(e)}")
            return None

    async def download_file(self, s3_path: str, local_path: str) -> bool:
        """Download a file from S3.

        Args:
            s3_path: Path of file in S3 bucket
            local_path: Local path to save downloaded file

        Returns:
            True if successful, False if failed
        """
        try:
            self.s3_client.download_file(self.bucket_name, s3_path, local_path)
            logger.info(f"Successfully downloaded {s3_path} to {local_path}")
            return True

        except ClientError as e:
            logger.error(f"Failed to download file from S3: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {str(e)}")
            return False
