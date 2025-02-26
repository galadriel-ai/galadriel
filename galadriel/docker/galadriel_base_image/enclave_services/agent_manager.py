import psutil
import logging
import signal
import time
from typing import Optional

logger = logging.getLogger(__name__)


def stop_agent(timeout: float = 60.0) -> bool:
    """Find python process running `agent.py`, send SIGTERM, and wait for termination.

    Args:
        timeout: Maximum time in seconds to wait for the process to terminate.
               After timeout, returns False if process is still running.

    Returns:
        bool: True if agent process was found and terminated, False otherwise.
    """
    agent_process: Optional[psutil.Process] = None

    try:
        # Find the agent process
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if "python" in proc.info["name"]:
                    print(proc.info)
                    cmdline = proc.info.get("cmdline", [])
                    if any("agent.py" in arg for arg in cmdline):
                        agent_process = proc
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if not agent_process:
            logger.warning("No running agent.py process found")
            return False

        # Send SIGTERM
        logger.info(f"Sending SIGTERM to agent process (PID: {agent_process.pid})")
        agent_process.send_signal(signal.SIGTERM)

        # Wait for the process to terminate
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not agent_process.is_running():
                logger.info(f"Agent process (PID: {agent_process.pid}) terminated successfully")
                return True
            time.sleep(0.1)

        # Process didn't terminate within timeout
        logger.warning(f"Agent process (PID: {agent_process.pid}) did not terminate within {timeout} seconds")
        return False

    except Exception as e:
        logger.error(f"Error while trying to stop agent: {e}")
        return False


if __name__ == "__main__":
    print(stop_agent())
