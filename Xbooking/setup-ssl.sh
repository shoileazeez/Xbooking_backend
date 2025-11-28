#!/bin/bash

# =============================================================================
# SSL Certificate Setup Script (Let's Encrypt)
# =============================================================================

set -e

# Check if domain is provided
if [ -z "$1" ]; then
    echo "Usage: ./setup-ssl.sh yourdomain.com [email@example.com]"
    exit 1
fi

DOMAIN=$1
EMAIL=${2:-"admin@$DOMAIN"}

echo "🔒 Setting up SSL for $DOMAIN..."

# Create directories
mkdir -p certbot/conf certbot/www

# Update nginx config with your domain
sed -i "s/yourdomain.com/$DOMAIN/g" nginx/conf.d/default.conf

# Restart nginx to apply domain changes
docker-compose restart nginx

# Get SSL certificate
docker-compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN

# Enable HTTPS in nginx config
echo "📝 Enabling HTTPS configuration..."
echo "Please manually uncomment the HTTPS server block in nginx/conf.d/default.conf"
echo "And comment out the HTTP server block (keep the redirect)"

# Restart nginx
docker-compose restart nginx

echo "✅ SSL setup complete!"
echo "🔒 Your site should now be accessible at https://$DOMAIN"
