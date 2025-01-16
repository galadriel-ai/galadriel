FROM amazonlinux:2023.6.20250107.0

# Install python for running the server and net-tools for modifying network config
RUN yum update -y
RUN yum groupinstall "Development Tools" -y
RUN yum install openssl-devel bzip2-devel libffi-devel wget net-tools git iproute dnsmasq logrotate -y
# stop DNS service (just in case)
RUN systemctl disable systemd-resolved

WORKDIR /tmp
RUN wget https://www.python.org/ftp/python/3.12.8/Python-3.12.8.tgz
RUN tar -xf Python-3.12.8.tgz 
RUN cd Python-3.12.8/ && ./configure --enable-optimizations
RUN cd Python-3.12.8/ && make -j $(nproc)
RUN cd Python-3.12.8/ && make altinstall && make clean

WORKDIR /app

COPY enclave_services/requirements.txt ./
RUN python3.12 -m pip install -r /app/requirements.txt

COPY enclave_services /app/enclave_services
COPY run.sh ./

RUN chmod +x run.sh

ENTRYPOINT ["/app/run.sh"]
