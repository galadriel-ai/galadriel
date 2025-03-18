"""Base class for Terminal tools."""

from abc import ABC

from e2b_code_interpreter import Sandbox

from galadriel.tools import Tool


class TerminalBaseTool(Tool, ABC):
    """Base class for Terminal tools that require E2B Sandbox.

    This class provides common terminal functionality for tools that need
    to interact with the terminal using a sandbox. It handles
    sandbox initialization and provides access to the sandbox.

    Attributes:
        sandbox (Sandbox): The sandbox instance for handling terminal operations

    Example:
        class TerminalCommandTool(TerminalBaseTool):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Additional initialization here

            def forward(self, ...):
                # Use sandbox for terminal operations
                self.sandbox.commands.run("ls -l")
    """

    def __init__(self, sandbox: Sandbox, *args, **kwargs):
        """Initialize the Terminal tool.

        Args:
            sandbox (Sandbox): The sandbox instance for handling terminal operations
            *args: Variable length argument list passed to parent Tool class
            **kwargs: Arbitrary keyword arguments passed to parent Tool class
        """
        self.sandbox = sandbox

        # Initialize parent Tool class
        super().__init__(*args, **kwargs)
