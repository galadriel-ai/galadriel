import logging
import socket
import threading
from attestation_manager import AttestationManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()


class EnclaveServer:
    # The default vsock port
    PORT = 8000
    BUFFER_SIZE = 1024

    def __init__(self):
        self.attestation_manager = AttestationManager()

    def start(self):
        """Start the vsock server."""
        try:
            with socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM) as server:
                server.bind((socket.VMADDR_CID_ANY, self.PORT))
                server.listen()
                logger.info(f"Enclave server listening on vsock port {self.PORT}")
                while True:
                    try:
                        conn, _ = server.accept()
                        threading.Thread(
                            target=self._handle_client, args=(conn,)
                        ).start()
                    except Exception as e:
                        logger.error(f"Error accepting connection: {e}")
        except Exception as e:
            logger.critical(f"Critical server error: {e}")

    def _handle_client(self, conn):
        """Handle individual client connections."""
        try:
            with conn:
                data = conn.recv(self.BUFFER_SIZE).decode()
                if not data:
                    logger.info("Client disconnected")
                    return
                logger.info(f"Received data: {data}")
                response = self.attestation_manager.handle_request(data)
                conn.sendall(response.encode())
        except Exception as e:
            logger.error(f"Error while handling client connection: {e}")
