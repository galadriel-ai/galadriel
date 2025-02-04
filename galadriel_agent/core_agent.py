from smolagents import *

from smolagents import CodeAgent as SmolAgentCodeAgent


class CodeAgent(SmolAgentCodeAgent):

    # Our interface here :)
    def run(*args, **kwargs):
        print("running")

