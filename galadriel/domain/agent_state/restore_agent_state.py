from typing import Any
from typing import Dict

from galadriel.core_agent import AgentMemory
from galadriel.core_agent import MultiStepAgent
from galadriel.core_agent import ActionStep
from galadriel.core_agent import MemoryStep
from galadriel.core_agent import PlanningStep
from galadriel.core_agent import TaskStep
from galadriel.core_agent import SystemPromptStep
from galadriel.entities import AgentState


def execute(agent: MultiStepAgent, agent_state: AgentState):
    # restore steps from agent_state
    assert (
        agent_state.agent_id == agent.agent_id
    ), "Agent ID in AgentState does not match the agent ID."
    assert agent_state.type == str(
        type(agent)
    ), "Agent type in AgentState does not match the agent type."

    memory_steps = []
    system_prompt_step = None
    for step in agent_state.steps:
        memory_step = _restore_memory_step(step)
        if isinstance(memory_step, SystemPromptStep):
            system_prompt_step = memory_step
            continue
        memory_steps.append(memory_step)

    assert system_prompt_step is not None, "SystemPromptStep is required in AgentState."

    memory = AgentMemory(system_prompt_step.system_prompt, memory_steps)
    memory.steps = memory_steps
    agent.memory = memory


def _restore_memory_step(data: Dict[str, Any]) -> MemoryStep:
    """Detects the correct MemoryStep subclass based on the dictionary keys and restores it."""
    if "tool_calls" in data and "model_output" in data:
        return ActionStep(**data)
    elif "facts" in data and "plan" in data:
        return PlanningStep(**data)
    elif "task" in data:
        return TaskStep(**data)
    elif "system_prompt" in data:
        return SystemPromptStep(**data)
    else:
        raise ValueError("Unknown MemoryStep type based on dictionary keys.")


if __name__ == "__main__":
    execute(
        MultiStepAgent(tools=[], model="gpt-4o-mini"),
        AgentState(steps=[{"task": "hello"}]),
    )
