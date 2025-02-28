import socket
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()


class InboundChatForwarder:
    BUFFER_SIZE = 8192
    TARGET_HOST = "localhost"
    TARGET_PORT = 8000

    def __init__(self, vsock_port: int):
        """
        Initialize the inbound chat forwarder.

        Args:
            vsock_port: The VSOCK port to listen on
        """
        self.vsock_port = vsock_port

    def forward(self, source, destination):
        """Forward data between two sockets."""
        string = " "
        while string:
            try:
                string = source.recv(self.BUFFER_SIZE)
                if string:
                    destination.sendall(string)
                else:
                    # End of data in this direction
                    try:
                        source.shutdown(socket.SHUT_RD)
                    except Exception:
                        pass
                    try:
                        destination.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
                    break
            except Exception as exc:
                logger.error(f"Exception in forward: {exc}")
                break

    def start(self):
        """Start the inbound chat forwarding service."""
        try:
            # Create VSOCK server socket
            vsock_server = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
            vsock_server.bind((socket.VMADDR_CID_ANY, self.vsock_port))
            vsock_server.listen(5)

            logger.info(f"Inbound chat forwarder listening on VSOCK port {self.vsock_port}")
            logger.info(f"Forwarding traffic to {self.TARGET_HOST}:{self.TARGET_PORT}")

            while True:
                client_socket, client_addr = vsock_server.accept()
                logger.info(f"Accepted connection from CID: {client_addr[0]}, Port: {client_addr[1]}")

                try:
                    # Connect to target server
                    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server_socket.connect((self.TARGET_HOST, self.TARGET_PORT))

                    # Create two threads to handle bidirectional data flow
                    client_to_server = threading.Thread(target=self.forward, args=(client_socket, server_socket))

                    server_to_client = threading.Thread(target=self.forward, args=(server_socket, client_socket))

                    # Start the threads
                    client_to_server.start()
                    server_to_client.start()
                except Exception as exc:
                    logger.error(f"Failed to establish connection to target: {exc}")
                    try:
                        client_socket.close()
                    except Exception:
                        pass

        except Exception as exc:
            logger.error(f"InboundChatForwarder exception: {exc}")
