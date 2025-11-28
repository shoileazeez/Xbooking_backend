#!/bin/bash

# =============================================================================
# Generate Self-Signed SSL Certificate for IP Address
# =============================================================================

set -e

# Get server IP or use provided argument
SERVER_IP=${1:-$(curl -s ifconfig.me)}

echo "🔒 Generating self-signed SSL certificate for IP: $SERVER_IP"

# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate (valid for 365 days)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/privkey.pem \
    -out ssl/fullchain.pem \
    -subj "/C=US/ST=State/L=City/O=XBooking/CN=$SERVER_IP" \
    -addext "subjectAltName=IP:$SERVER_IP"

echo "✅ SSL certificate generated!"
echo "   Certificate: ssl/fullchain.pem"
echo "   Private Key: ssl/privkey.pem"
echo ""
echo "⚠️  Note: This is a self-signed certificate."
echo "   Browsers will show a security warning - click 'Advanced' and 'Proceed' to continue."
echo "   For production, use a domain with Let's Encrypt instead."
