#!/bin/bash

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Flush existing NAT rules (optional, ensures a clean setup)
/usr/sbin/iptables-legacy -t nat -F

# Redirect all outgoing TCP traffic on port 443 to localhost:4443
/usr/sbin/iptables-legacy -t nat -A OUTPUT -p tcp --dport 443 ! -d 127.0.0.1 -j DNAT --to-destination 127.0.0.1:4443

iptables -t nat -A POSTROUTING -o lo -s 0.0.0.0 -j SNAT --to-source 127.0.0.1

echo "All outgoing HTTPS traffic is now redirected to localhost:4443."