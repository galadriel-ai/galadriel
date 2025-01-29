#!/bin/bash

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Flush existing NAT rules (optional, ensures a clean setup)
iptables -t nat -F

# Redirect all outgoing TCP traffic on port 443 to localhost:4443
iptables -t nat -A OUTPUT -p tcp --dport 443 ! -d 127.0.0.1 -j DNAT --to-destination 127.0.0.1:4443

# Redirect all DNS queries (UDP) to local port 5053
iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-port 5053

# Ensure the source address is properly rewritten to localhost
iptables -t nat -A POSTROUTING -o lo -j MASQUERADE

echo "All outgoing HTTPS traffic is now redirected to localhost:4443."