from galadriel_agent.core_agent import CodeAgent
from galadriel_agent.core_agent import LiteLLMModel

if __name__ == '__main__':
    a = CodeAgent(
        tools=[],
        model=LiteLLMModel()
    )
    a.run()
