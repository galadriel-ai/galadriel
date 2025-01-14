#!/bin/bash

# Assign an IP address to local loopback
ip addr add 127.0.0.1/32 dev lo

ip link set dev lo up

# Add a hosts record, pointing target site calls to local loopback
echo "127.0.0.1   api.openai.com" >> /etc/hosts

#mkdir -p /run/resolvconf
#echo "nameserver 127.0.0.1" > /run/resolvconf/resolv.conf

# Start the server
echo "Starting enclave serivces"
python3.12 /app/enclave_services/main.py &
