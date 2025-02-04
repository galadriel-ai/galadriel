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
    REMOTE_PORT_OPENAI = 8001
    REMOTE_PORT_DISCORD = 8002
    REMOTE_PORT_GALADRIEL = 8003
    REMOTE_PORT_PREPLEXITY = 8004
    REMOTE_PORT_TELEGRAM = 8005
    REMOTE_PORT_TWITTER = 8006
    REMOTE_PORT_S3 = 8007
    REMOTE_PORT_DEXSCREENER = 8008
    REMOTE_PORT_COINGECKO = 8009

    REMOTE_PORTS = {
        "api.openai.com": REMOTE_PORT_OPENAI,
        "discord.com": REMOTE_PORT_DISCORD,
        "api.galadriel.com": REMOTE_PORT_GALADRIEL,
        "api.preplexity.ai": REMOTE_PORT_PREPLEXITY,
        "api.telegram.org": REMOTE_PORT_TELEGRAM,
        "api.twitter.com": REMOTE_PORT_TWITTER,
        "agents-memory-storage.s3.us-east-1.amazonaws.com": REMOTE_PORT_S3,
        "api.dexscreener.com": REMOTE_PORT_DEXSCREENER,
        "api.coingecko.com": REMOTE_PORT_COINGECKO,
    }

    def __init__(self, local_ip: str, local_port: int):
        self.local_ip = local_ip
        self.local_port = local_port

    def guess_the_destination_port(self, data: bytes) -> int:
        # This is a simple heuristic, we look for the domain name in the SSL handshake data
        # and return the corresponding VSOCK port
        #
        # https://wiki.osdev.org/TLS_Handshake#Client_Hello_Message
        text = data.decode("utf-8", errors="ignore")
        for url, port in self.REMOTE_PORTS.items():
            if url in text:
                print(f"Got destination port: {port} for url: {url}")
                return port
        # TODO: what if no destination?
        print("Error, did not get a destination port!\n")
        return self.REMOTE_PORT_OPENAI

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
                destination_port = self.guess_the_destination_port(data)

                server_socket = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
                server_socket.connect((self.REMOTE_CID, destination_port))

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
