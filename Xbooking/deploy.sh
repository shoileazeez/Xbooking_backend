#!/bin/bash

# =============================================================================
# XBooking VPS/Droplet Deployment Script
# =============================================================================

set -e

echo "🚀 Starting XBooking Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

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
    echo -e "${RED}❌ .env.production file not found!${NC}"
    echo -e "${YELLOW}Creating from example...${NC}"
    cp .env.production.example .env.production
    echo -e "${RED}⚠️  Please edit .env.production with your actual values!${NC}"
    echo "Run: nano /opt/xbooking/Xbooking/.env.production"
    exit 1
fi

# Create required directories
mkdir -p certbot/conf certbot/www

# Build and start containers
echo -e "${YELLOW}🏗️  Building Docker images...${NC}"
docker-compose build

echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 10

# Check if services are running
echo -e "${YELLOW}🔍 Checking service status...${NC}"
docker-compose ps

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📋 Useful commands:"
echo "  - View logs:        docker-compose logs -f"
echo "  - View web logs:    docker-compose logs -f web"
echo "  - View worker logs: docker-compose logs -f celery_worker"
echo "  - Restart services: docker-compose restart"
echo "  - Stop services:    docker-compose down"
echo ""
echo "🌐 Your app should be accessible at: http://your-server-ip"
