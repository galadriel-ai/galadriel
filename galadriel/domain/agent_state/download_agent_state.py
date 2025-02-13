import json
from typing import Optional

from galadriel.entities import AgentState
from galadriel.errors import AgentStateError
from galadriel.repository.s3_repository import S3Repository


def execute(repository: S3Repository, agent_id: str, key: Optional[str]) -> AgentState:
    agent_state = repository.download_agent_state(agent_id, key)
    if agent_state is None:
        raise AgentStateError("Failed to download agent state")
    return agent_state
