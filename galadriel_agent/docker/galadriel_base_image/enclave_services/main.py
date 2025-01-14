import logging
import signal
import sys

from enclave_server import EnclaveServer
from traffic_forwarder import TrafficForwarder

LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 443


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()


def signal_handler(sig, frame):
    """Handle termination signals."""
    logger.info("Shutting down server gracefully...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    enclave_server = EnclaveServer()
    traffic_forwarder = TrafficForwarder(LOCAL_IP, LOCAL_PORT)

    enclave_server.start()
    traffic_forwarder.start()


if __name__ == "__main__":
    main()
