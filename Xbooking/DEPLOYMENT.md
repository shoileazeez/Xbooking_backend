# XBooking VPS/Droplet Deployment Guide

## Prerequisites
- A VPS/Droplet with Ubuntu 20.04+ (DigitalOcean, Linode, Vultr, Hetzner, etc.)
- Minimum 1GB RAM, 1 CPU (2GB RAM recommended)
- A domain name (optional but recommended)
- SSH access to your server

---

## Quick Deployment (5 minutes)

### Step 1: SSH into your server
```bash
ssh root@your-server-ip
```

### Step 2: Clone the repository
```bash
cd /opt
git clone https://github.com/shoileazeez/Xbooking_backend.git xbooking
cd xbooking/Xbooking
```

### Step 3: Create environment file
```bash
cp .env.production.example .env.production
nano .env.production
```

Edit the following values:
```env
SECRET_KEY=generate-a-strong-secret-key
ALLOWED_HOSTS=your-domain.com,your-server-ip
POSTGRES_PASSWORD=your-strong-db-password
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
PAYSTACK_SECRET_KEY=your-paystack-key
# ... other settings
```

### Step 4: Run deployment script
```bash
chmod +x deploy.sh
./deploy.sh
```

### Step 5: Verify deployment
```bash
docker-compose ps
```

You should see all services running:
- xbooking_web
- xbooking_db
- xbooking_redis
- xbooking_celery_worker
- xbooking_celery_beat
- xbooking_nginx

---

## Manual Deployment (Step by Step)

### 1. Update System
```bash
apt-get update && apt-get upgrade -y
```

### 2. Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl enable docker
systemctl start docker
```

### 3. Install Docker Compose
```bash
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### 4. Clone Repository
```bash
mkdir -p /opt/xbooking
cd /opt/xbooking
git clone https://github.com/shoileazeez/Xbooking_backend.git .
cd Xbooking
```

### 5. Configure Environment
```bash
cp .env.production.example .env.production
nano .env.production
```

### 6. Build and Start
```bash
docker-compose build
docker-compose up -d
```

---

## SSL/HTTPS Setup (Free with Let's Encrypt)

### Option 1: Automated Script
```bash
chmod +x setup-ssl.sh
./setup-ssl.sh yourdomain.com your-email@gmail.com
```

### Option 2: Manual Setup
```bash
# 1. Update nginx config with your domain
sed -i 's/yourdomain.com/your-actual-domain.com/g' nginx/conf.d/default.conf

# 2. Restart nginx
docker-compose restart nginx

# 3. Get SSL certificate
docker-compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email your-email@gmail.com \
    --agree-tos \
    --no-eff-email \
    -d your-actual-domain.com \
    -d www.your-actual-domain.com

# 4. Enable HTTPS in nginx (edit nginx/conf.d/default.conf)
nano nginx/conf.d/default.conf
# Uncomment the HTTPS server block and update domain names

# 5. Restart nginx
docker-compose restart nginx
```

---

## Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
docker-compose logs -f nginx
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart web
docker-compose restart celery_worker
```

### Stop Services
```bash
docker-compose down
```

### Update Application
```bash
cd /opt/xbooking/Xbooking
git pull origin main
docker-compose build
docker-compose up -d
```

### Access Django Shell
```bash
docker-compose exec web python manage.py shell
```

### Create Superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

### Run Migrations
```bash
docker-compose exec web python manage.py migrate
```

### View Database
```bash
docker-compose exec db psql -U xbooking_user -d xbooking
```

---

## Firewall Setup

```bash
# Install UFW
apt-get install -y ufw

# Allow SSH
ufw allow 22

# Allow HTTP and HTTPS
ufw allow 80
ufw allow 443

# Enable firewall
ufw enable

# Check status
ufw status
```

---

## Monitoring

### Check Resource Usage
```bash
docker stats
```

### Check Disk Space
```bash
df -h
```

### Clean Up Docker Resources
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove all unused resources
docker system prune -a
```

---

## Troubleshooting

### Web service not starting
```bash
docker-compose logs web
```

### Database connection issues
```bash
# Check if database is running
docker-compose ps db

# Check database logs
docker-compose logs db
```

### Celery not processing tasks
```bash
# Check worker logs
docker-compose logs celery_worker

# Check Redis connection
docker-compose exec redis redis-cli ping
```

### Nginx 502 Bad Gateway
```bash
# Check if web service is running
docker-compose ps web

# Restart services
docker-compose restart
```

---

## Backup

### Database Backup
```bash
# Create backup
docker-compose exec db pg_dump -U xbooking_user xbooking > backup_$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T db psql -U xbooking_user xbooking < backup_20231128.sql
```

### Full Backup Script
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T db pg_dump -U xbooking_user xbooking > $BACKUP_DIR/db_$DATE.sql

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /var/lib/docker/volumes/*media*

echo "Backup completed: $BACKUP_DIR"
```

---

## Cost Comparison (Monthly)

| Provider | Plan | RAM | CPU | Storage | Price |
|----------|------|-----|-----|---------|-------|
| DigitalOcean | Basic Droplet | 1GB | 1 | 25GB | $6/mo |
| Vultr | Cloud Compute | 1GB | 1 | 25GB | $5/mo |
| Linode | Nanode | 1GB | 1 | 25GB | $5/mo |
| Hetzner | CX11 | 2GB | 1 | 20GB | €3.29/mo |
| Oracle Cloud | Always Free | 1GB | 1 | 50GB | FREE |

**Recommended**: Start with 1GB RAM, upgrade to 2GB if needed for better Celery performance.

---

## Architecture

```
                    ┌─────────────┐
                    │   Nginx     │ ← Port 80/443
                    │  (Reverse   │
                    │   Proxy)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Django    │ ← Port 8000
                    │  (Gunicorn) │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
   │  PostgreSQL │  │    Redis    │  │   Celery    │
   │  (Database) │  │  (Broker)   │  │  (Worker +  │
   │             │  │             │  │    Beat)    │
   └─────────────┘  └─────────────┘  └─────────────┘
```

---

## Support

If you encounter any issues:
1. Check the logs: `docker-compose logs -f`
2. Verify all services are running: `docker-compose ps`
3. Ensure environment variables are set correctly
4. Check firewall settings
