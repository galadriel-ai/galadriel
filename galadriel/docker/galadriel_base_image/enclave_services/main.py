import logging
import signal
import sys
import threading

# pylint: disable=E0401
from dns_forwarder import DNSForwarder
from enclave_server import EnclaveServer
from inbound_chat_forwarder import InboundChatForwarder
from traffic_forwarder import TrafficForwarder

LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 4443
CHAT_PORT = 8001


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()


def signal_handler():
    """Handle termination signals."""
    logger.info("Shutting down server gracefully...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    dns_forwarder = DNSForwarder()
    enclave_server = EnclaveServer()
    traffic_forwarder = TrafficForwarder(LOCAL_IP, LOCAL_PORT)
    inbound_chat_forwarder = InboundChatForwarder(CHAT_PORT)

    dns_thread = threading.Thread(target=dns_forwarder.start)
    enclave_thread = threading.Thread(target=enclave_server.start)
    forwarder_thread = threading.Thread(target=traffic_forwarder.start)
    inbound_chat_forwarder_thread = threading.Thread(target=inbound_chat_forwarder.start)

    dns_thread.start()
    enclave_thread.start()
    forwarder_thread.start()
    inbound_chat_forwarder_thread.start()

    dns_thread.join()
    enclave_thread.join()
    forwarder_thread.join()


if __name__ == "__main__":
    main()
