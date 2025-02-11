FROM amazonlinux:2023.6.20250107.0

# Install python 3.12
RUN dnf install iproute shadow-utils iptables-legacy sqlite-devel python3.12 python3.12-pip -y

WORKDIR /app

COPY enclave_services/requirements.txt ./
RUN python3.12 -m pip install -r /app/requirements.txt

COPY enclave_services /app/enclave_services
COPY run.sh ./
COPY setup_forwarding.sh ./

RUN chmod +x setup_forwarding.sh
RUN chmod +x run.sh

CMD ["/app/run.sh"]
