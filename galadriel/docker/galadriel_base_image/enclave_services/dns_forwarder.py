import socket


class DNSForwarder:
    VSOCK_CID = 3  # Host CID
    VSOCK_PORT = 5053  # VSOCK port on host
    LOCAL_PORT = 53  # Local DNS listener in enclave

    def forward_dns_request(self, dns_request):
        """Send DNS request via vsock and return the response."""
        with socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM) as vsock:
            vsock.connect((self.VSOCK_CID, self.VSOCK_PORT))
            vsock.sendall(dns_request)

            # Receive the DNS response
            response = vsock.recv(512)  # Typical DNS response size
            return response

    def start(self):
        """Listen on TCP & UDP port 53 and forward DNS requests via vsock."""
        # UDP socket for DNS queries
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind(("127.0.0.1", self.LOCAL_PORT))

        print(f"Enclave DNS forwarder listening on 127.0.0.1:{self.LOCAL_PORT}...")

        while True:
            dns_request, client_addr = udp_sock.recvfrom(512)  # Typical DNS query size
            print(f"Received DNS request from {client_addr}")

            # Forward to vsock
            dns_response = self.forward_dns_request(dns_request)

            # Send response back to the requesting application
            udp_sock.sendto(dns_response, client_addr)
