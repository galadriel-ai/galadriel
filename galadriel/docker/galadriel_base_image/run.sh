#!/bin/bash

# Assign an IP address to local loopback
ip addr add 127.0.0.1/32 dev lo

ip link set dev lo up

# Add a route to the default gateway
ip route add default dev lo src 127.0.0.1

# Verify routing table
ip route show

echo "nameserver 127.0.0.1" > /etc/resolv.conf

# Add a hosts record, pointing target site calls to local loopback

# Setup forwarding
/app/setup_forwarding.sh

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
python3.12 agent.py