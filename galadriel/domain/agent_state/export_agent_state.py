from galadriel.core_agent import MultiStepAgent
from galadriel.entities import AgentState


def execute(agent_id: str, agent: MultiStepAgent) -> AgentState:
    steps = [agent.memory.system_prompt.dict()]
    for step in agent.memory.steps:
        steps.append(step.dict())
    return AgentState(agent_id=agent_id, type=str(type(agent)), steps=steps)
