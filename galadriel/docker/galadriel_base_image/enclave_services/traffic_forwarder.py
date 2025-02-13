import socket
import struct
import threading
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()


class TrafficForwarder:
    BUFFER_SIZE = 1024
    REMOTE_PORT = 8001
    REMOTE_CID = 3  # The CID of the TEE host

    def __init__(self, local_ip: str, local_port: int):
        self.local_ip = local_ip
        self.local_port = local_port

    def get_original_destination(self, client_socket):
        """
        Retrieves the original destination IP and port using SO_ORIGINAL_DST.
        """
        try:
            original_dst = client_socket.getsockopt(socket.SOL_IP, 80, 16)
            port, ip_raw = struct.unpack_from("!2xH4s8x", original_dst)
            original_ip = socket.inet_ntoa(ip_raw)
            return original_ip, port
        except Exception as exc:
            logger.error(f"Failed to get original destination: {exc}")
            return None, None

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

            logger.info(f"Traffic forwarder listening on {self.local_ip}:{self.local_port}")
            while True:
                client_socket = dock_socket.accept()[0]
                original_ip, original_port = self.get_original_destination(client_socket)
                if not original_ip or not original_port:
                    logger.info("Failed to get original destination, closing connection")
                    client_socket.close()
                    continue

                logger.info(f"Forwarding traffic to {original_ip}:{original_port}")
                data = client_socket.recv(self.BUFFER_SIZE)
                ip_encoded = socket.inet_aton(original_ip)  # Convert IP to 4-byte binary
                port_encoded = struct.pack("!H", original_port)  # Convert port to 2-byte binary
                destination_and_data = ip_encoded + port_encoded + data

                server_socket = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
                server_socket.connect((self.REMOTE_CID, self.REMOTE_PORT))

                outgoing_thread = threading.Thread(
                    target=self.forward,
                    args=(client_socket, server_socket, destination_and_data),
                )
                incoming_thread = threading.Thread(target=self.forward, args=(server_socket, client_socket))

                outgoing_thread.start()
                incoming_thread.start()
        except Exception as exc:
            logger.error(f"TrafficForwarder exception: {exc}")
