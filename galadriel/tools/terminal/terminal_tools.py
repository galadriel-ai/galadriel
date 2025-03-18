from typing import Optional

from e2b_code_interpreter import Sandbox

from galadriel.tools.terminal.base import TerminalBaseTool

from galadriel.logging_utils import get_agent_logger

TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50


logger = get_agent_logger()


class RunCommandTool(TerminalBaseTool):
    """Run a shell command and return the result.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "run_command"
    description = "Run a shell command and return the result."
    inputs = {
        "command": {
            "type": "string",
            "description": "The command to run.",
        },
    }
    output_type = "string"

    def __init__(self, sandbox: Sandbox, *args, **kwargs):
        super().__init__(sandbox, *args, **kwargs)

    def forward(self, command: str) -> Optional[str]:
        """Run a shell command and return the result.

        Args:
            command (str): The command to run.

        Returns:
            Optional[str]: The result of the command if successful, None if error
        """
        try:
            result = self.sandbox.commands.run(command, timeout=5)
            return result.stdout
        except Exception as error:
            logger.error(f"Failed to run command: {str(error)}")
            return None


class RunCommandInBackgroundTool(TerminalBaseTool):
    """Run a shell command in the background and return a message.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "run_command_in_background"
    description = "Run a shell command in the background and return a message."
    inputs = {
        "command": {
            "type": "string",
            "description": "The command to run.",
        },
    }
    output_type = "string"

    def __init__(self, sandbox: Sandbox, *args, **kwargs):
        super().__init__(sandbox, *args, **kwargs)

    def forward(self, command: str) -> str:
        """Run a shell command and return the result.

        Args:
            command (str): The command to run.

        Returns:
            Optional[str]: The result of the command if successful, None if error
        """
        try:
            self.sandbox.commands.run(command, background=True)
            return "The command has been started."
        except Exception as error:
            logger.error(f"Failed to run command: {str(error)}")
            return None


class SendKeyTool(TerminalBaseTool):
    """Send a key or combination of keys to the system.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "send_key"
    description = "Send a key or combination of keys to the system."
    inputs = {
        "key": {
            "type": "string",
            "description": "Key or combination (e.g. 'Return', 'Ctl-C')",
        },
    }
    output_type = "string"

    def __init__(self, sandbox: Sandbox, *args, **kwargs):
        super().__init__(sandbox, *args, **kwargs)

    def forward(self, key: str) -> str:
        """Send a key or combination of keys to the system.

        Args:
            key (str): The key to send.

        Returns:
            Optional[str]: The result of the command if successful, None if error
        """
        try:
            self.sandbox.press(key)
            return "The key has been pressed."
        except Exception as error:
            logger.error(f"Failed to send key: {str(error)}")
            return None


class TypeTextTool(TerminalBaseTool):
    """Type a specified text into the system.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "type_text"
    description = "Type a specified text into the system."
    inputs = {
        "text": {
            "type": "string",
            "description": "The text to type.",
        },
    }
    output_type = "string"

    def __init__(self, sandbox: Sandbox, *args, **kwargs):
        super().__init__(sandbox, *args, **kwargs)

    def forward(self, text: str) -> str:
        """Type a specified text into the system.

        Args:
            text (str): The text to type.

        Returns:
            Optional[str]: The result of the command if successful, None if error
        """
        try:
            self.sandbox.write(text, chunk_size=TYPING_GROUP_SIZE, delay_in_ms=TYPING_DELAY_MS)
            return "The text has been typed."
        except Exception as error:
            logger.error(f"Failed to type text: {str(error)}")
            return None


class ReadFileTool(TerminalBaseTool):
    """Read a specified file and return the result.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "read_file"
    description = "Read a specified file and return the content."
    inputs = {
        "file": {
            "type": "string",
            "description": "The file to read.",
        },
    }
    output_type = "string"

    def __init__(self, sandbox: Sandbox, *args, **kwargs):
        super().__init__(sandbox, *args, **kwargs)

    def forward(self, file: str) -> Optional[str]:
        """Read a specified file and return the content.

        Args:
            file (str): The file to read.

        Returns:
            Optional[str]: The content of the file if successful, None if error
        """
        try:
            return self.sandbox.files.read(file)
        except Exception as error:
            logger.error(f"Failed to read file: {str(error)}")
            return None


class WriteFileTool(TerminalBaseTool):
    """Write a specified text to a file.

    Attributes:
        name (str): Tool identifier
        description (str): Description of the tool's functionality
        inputs (dict): Schema for required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "write_file"
    description = "Write a specified text to a file."
    inputs = {
        "file": {
            "type": "string",
            "description": "The file to write to.",
        },
        "content": {
            "type": "string",
            "description": "The content to write to the file.",
        },
    }
    output_type = "string"

    def __init__(self, sandbox: Sandbox, *args, **kwargs):
        super().__init__(sandbox, *args, **kwargs)

    def forward(self, file: str, content: str) -> str:
        """Write a specified text to a file.

        Args:
            file (str): The file to write to.
            content (str): The content to write to the file.

        Returns:
            Optional[str]: The result of the command if successful, None if error
        """
        try:
            self.sandbox.files.write(file, content)
            return "The file has been written."
        except Exception as error:
            logger.error(f"Failed to write file: {str(error)}")
            return None
