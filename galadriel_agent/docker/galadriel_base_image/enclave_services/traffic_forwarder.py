import socket
import threading
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()


class TrafficForwarder:
    BUFFER_SIZE = 1024
    PORT = 8000
    REMOTE_CID = 3  # The CID of the TEE host

    def __init__(self, local_ip: str, local_port: int):
        self.local_ip = local_ip
        self.local_port = local_port

    def forward(self, source, destination, first_string: Optional[bytes] = None):
        """Forward data between two sockets."""
        if first_string:
            destination.sendall(first_string)

        string = " "
        while string:
            try:
                string = source.recv(self.BUFFER_SIZE)
                if string:
                    destination.sendall(string)
                else:
                    source.shutdown(socket.SHUT_RD)
                    destination.shutdown(socket.SHUT_WR)
            except Exception as exc:
                logger.error(f"Exception in forward: {exc}")

    def start(self):
        """Traffic forwarding service."""
        try:
            dock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dock_socket.bind((self.local_ip, self.local_port))
            dock_socket.listen(5)

            logger.info(
                f"Traffic forwarder listening on {self.local_ip}:{self.local_port}"
            )
            while True:
                client_socket = dock_socket.accept()[0]
                data = client_socket.recv(self.BUFFER_SIZE)

                server_socket = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
                server_socket.connect((self.REMOTE_CID, self.PORT))

                outgoing_thread = threading.Thread(
                    target=self.forward, args=(client_socket, server_socket, data)
                )
                incoming_thread = threading.Thread(
                    target=self.forward, args=(server_socket, client_socket)
                )

                outgoing_thread.start()
                incoming_thread.start()
        except Exception as exc:
            logger.error(f"TrafficForwarder exception: {exc}")
