from typing import Optional

from galadriel.entities import AgentState
from galadriel.errors import AgentStateError
from galadriel.repository.s3_repository import S3Repository


def execute(
    repository: S3Repository, agent_state: AgentState, key: Optional[str]
) -> str:
    # Upload agent state to S3
    key = repository.upload_agent_state(agent_state, key)

    if key is None:
        raise AgentStateError("Failed to upload agent state")
    return key
