#!/bin/bash

# Assign an IP address to local loopback
ip addr add 127.0.0.1/32 dev lo

ip link set dev lo up

# Add a hosts record, pointing target site calls to local loopback
echo "127.0.0.1   api.openai.com" >> /etc/hosts
echo "127.0.0.1   discord.com" >> /etc/hosts
echo "127.0.0.1   api.galadriel.com" >> /etc/hosts
echo "127.0.0.1   api.preplexity.ai" >> /etc/hosts
echo "127.0.0.1   api.telegram.org" >> /etc/hosts
echo "127.0.0.1   api.twitter.com" >> /etc/hosts
echo "127.0.0.1   agents-memory-storage.s3.us-east-1.amazonaws.com" >> /etc/hosts

# Start the server
echo "Starting enclave services"
python3.12 /app/enclave_services/main.py &


# Wait for env vars to be set
python3.12 /app/enclave_services/env_var_service.py

# Source the exported environment variables
if [ -f /tmp/env_vars.sh ]; then
    echo "Loading environment variables..."
    source /tmp/env_vars.sh
else
    echo "No environment variables file found."
fi
# Continue with execution
cd /home/appuser/
python3.12 main.py