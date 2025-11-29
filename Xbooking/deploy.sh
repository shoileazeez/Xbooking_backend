#!/bin/bash

# =============================================================================
# XBooking VPS/Droplet Deployment Script (Domain + Let's Encrypt SSL)
# =============================================================================

set -e

echo "🚀 Starting XBooking Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Get domain from user
echo ""
read -p "Enter your domain (e.g., api.xbooking.com): " DOMAIN
read -p "Enter your email for SSL certificate: " EMAIL

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo -e "${RED}Domain and email are required!${NC}"
    exit 1
fi

echo -e "${BLUE}📌 Configuring for domain: $DOMAIN${NC}"

# Update system
echo -e "${YELLOW}📦 Updating system packages...${NC}"
apt-get update && apt-get upgrade -y

# Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
fi

# Install Docker Compose if not installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}🐳 Installing Docker Compose...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Install Git if not installed
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}📥 Installing Git...${NC}"
    apt-get install -y git
fi

# Create app directory
APP_DIR="/opt/xbooking"
echo -e "${YELLOW}📁 Setting up application directory...${NC}"
mkdir -p $APP_DIR
cd $APP_DIR

# Clone or pull repository
if [ -d ".git" ]; then
    echo -e "${YELLOW}📥 Pulling latest changes...${NC}"
    git pull origin main
else
    echo -e "${YELLOW}📥 Cloning repository...${NC}"
    git clone https://github.com/shoileazeez/Xbooking_backend.git .
fi

# Navigate to Django project directory
cd Xbooking

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}Creating .env.production from example...${NC}"
    cp .env.production.example .env.production
    
    # Update domain in .env.production
    sed -i "s/yourdomain.com/$DOMAIN/g" .env.production
    
    echo -e "${RED}⚠️  Please edit .env.production with your actual values!${NC}"
    echo "Run: nano /opt/xbooking/Xbooking/.env.production"
    echo ""
    echo "After editing, run this script again."
    exit 1
fi

# Update nginx config with domain
echo -e "${YELLOW}� Configuring Nginx for $DOMAIN...${NC}"
sed -i "s/yourdomain.com/$DOMAIN/g" nginx/conf.d/default.conf

# Create certbot directories
mkdir -p certbot/conf certbot/www

# Create temporary nginx config for initial certificate (HTTP only)
echo -e "${YELLOW}📝 Creating temporary Nginx config for SSL setup...${NC}"
cat > nginx/conf.d/default.conf.tmp << EOF
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Backup original SSL config and use temporary HTTP config
cp nginx/conf.d/default.conf nginx/conf.d/default.conf.ssl
mv nginx/conf.d/default.conf.tmp nginx/conf.d/default.conf

# Build and start containers
echo -e "${YELLOW}🏗️  Building Docker images...${NC}"
docker-compose build

echo -e "${YELLOW}🚀 Starting services (HTTP only for SSL setup)...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 15

# Obtain SSL certificate from Let's Encrypt
echo -e "${YELLOW}🔒 Obtaining SSL certificate from Let's Encrypt...${NC}"
docker-compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# Check if certificate was obtained
if [ -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${GREEN}✅ SSL certificate obtained successfully!${NC}"
    
    # Restore full SSL config
    mv nginx/conf.d/default.conf.ssl nginx/conf.d/default.conf
    
    # Restart nginx with SSL
    echo -e "${YELLOW}🔄 Restarting Nginx with SSL...${NC}"
    docker-compose restart nginx
else
    echo -e "${RED}❌ Failed to obtain SSL certificate!${NC}"
    echo "Make sure your domain DNS points to this server."
    echo "You can try again later with: ./setup-ssl.sh $DOMAIN $EMAIL"
    
    # Keep HTTP config for now
    rm -f nginx/conf.d/default.conf.ssl
fi

# Check if services are running
echo -e "${YELLOW}🔍 Checking service status...${NC}"
docker-compose ps

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "🌐 Your API is accessible at:"
echo -e "   ${BLUE}https://$DOMAIN/api/${NC}"
echo ""
echo -e "🔗 Payment Webhook URLs (use these in Paystack/Flutterwave dashboard):"
echo -e "   Paystack:     ${BLUE}https://$DOMAIN/api/payment/webhooks/paystack/${NC}"
echo -e "   Flutterwave:  ${BLUE}https://$DOMAIN/api/payment/webhooks/flutterwave/${NC}"
echo ""
echo -e "📋 Useful commands:"
echo -e "   View logs:        ${YELLOW}cd /opt/xbooking/Xbooking && docker-compose logs -f${NC}"
echo -e "   View web logs:    ${YELLOW}docker-compose logs -f web${NC}"
echo -e "   View worker logs: ${YELLOW}docker-compose logs -f celery_worker${NC}"
echo -e "   Restart services: ${YELLOW}docker-compose restart${NC}"
echo -e "   Stop services:    ${YELLOW}docker-compose down${NC}"
echo ""
echo -e "🔧 Admin panel: ${BLUE}https://$DOMAIN/admin/${NC}"
echo ""
