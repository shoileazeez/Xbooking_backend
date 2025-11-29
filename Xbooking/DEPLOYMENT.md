# XBooking Backend - VPS/Droplet Deployment Guide

Complete guide to deploy XBooking Backend on any VPS (DigitalOcean, Vultr, Linode, Hetzner, etc.) with **HTTPS**, **Celery workers**, and **automatic SSL** via Let's Encrypt.

---

## 📋 Prerequisites

1. **VPS/Droplet** with Ubuntu 20.04+ (minimum 1GB RAM, 1 CPU)
2. **Domain name** pointed to your server IP
3. **SSH access** to your server

---

## 🌐 Step 1: Point Your Domain to Server

Before deploying, configure your domain DNS:

| Type | Name | Value |
|------|------|-------|
| A | @ | YOUR_SERVER_IP |
| A | api | YOUR_SERVER_IP |
| A | www | YOUR_SERVER_IP |

**Example**: If your domain is `xbooking.com` and server IP is `165.22.100.50`:
- `xbooking.com` → `165.22.100.50`
- `api.xbooking.com` → `165.22.100.50`

⏰ **Wait 5-30 minutes** for DNS propagation before proceeding.

---

## 🚀 Step 2: Quick Deployment (5 minutes)

### SSH into your server:
```bash
ssh root@YOUR_SERVER_IP
```

### Run these commands:
```bash
# Clone repository
cd /opt
git clone https://github.com/shoileazeez/Xbooking_backend.git xbooking
cd xbooking/Xbooking

# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### The script will ask for:
1. **Your domain** (e.g., `api.xbooking.com`)
2. **Your email** (for SSL certificate notifications)

### First run - Configure environment:
```bash
# Edit the environment file with your values
nano .env.production
```

**Important values to change:**
```env
SECRET_KEY=generate-a-random-64-character-string
POSTGRES_PASSWORD=your-strong-database-password
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
PAYSTACK_SECRET_KEY=sk_live_your_key
PAYSTACK_PUBLIC_KEY=pk_live_your_key
```

### Run deployment again:
```bash
./deploy.sh
```

---

## 📁 What Gets Deployed

| Service | Description | Port |
|---------|-------------|------|
| **Django + Gunicorn** | Main web application | 8000 (internal) |
| **PostgreSQL** | Database | 5432 (internal) |
| **Redis** | Celery message broker | 6379 (internal) |
| **Celery Worker** | Background task processing | - |
| **Celery Beat** | Scheduled tasks | - |
| **Nginx** | Reverse proxy + SSL | 80, 443 |
| **Certbot** | SSL certificate renewal | - |

---

## 🔗 API Endpoints After Deployment

| Endpoint | URL |
|----------|-----|
| **API Base** | `https://yourdomain.com/api/` |
| **Admin Panel** | `https://yourdomain.com/admin/` |
| **Paystack Webhook** | `https://yourdomain.com/api/payment/webhooks/paystack/` |
| **Flutterwave Webhook** | `https://yourdomain.com/api/payment/webhooks/flutterwave/` |

---

## 💳 Configure Payment Webhooks

### Paystack Dashboard:
1. Go to **Settings** → **API Keys & Webhooks**
2. Set Webhook URL: `https://yourdomain.com/api/payment/webhooks/paystack/`
3. Copy your **Secret Key** to `.env.production`

### Flutterwave Dashboard:
1. Go to **Settings** → **Webhooks**
2. Set Webhook URL: `https://yourdomain.com/api/payment/webhooks/flutterwave/`
3. Copy your **Secret Key** to `.env.production`

---

## 🖥️ Frontend Integration

### Update your frontend environment:
```env
NEXT_PUBLIC_API_URL=https://yourdomain.com/api
# or for React/Vue
VITE_API_URL=https://yourdomain.com/api
```

### Example API calls:
```javascript
// Login
const response = await fetch('https://yourdomain.com/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});

// Get spaces
const spaces = await fetch('https://yourdomain.com/api/spaces/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## 📋 Useful Commands

### View logs:
```bash
cd /opt/xbooking/Xbooking

# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
docker-compose logs -f nginx
```

### Restart services:
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart web
docker-compose restart celery_worker
```

### Stop/Start services:
```bash
docker-compose down    # Stop all
docker-compose up -d   # Start all
```

### Access Django shell:
```bash
docker-compose exec web python manage.py shell
```

### Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

### Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

### Check service status:
```bash
docker-compose ps
```

---

## 🔄 Updating the Application

```bash
cd /opt/xbooking/Xbooking

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose build
docker-compose up -d

# Run migrations if needed
docker-compose exec web python manage.py migrate
```

---

## 🔒 SSL Certificate Renewal

SSL certificates auto-renew via the Certbot container. To manually renew:

```bash
docker-compose run --rm certbot renew
docker-compose restart nginx
```

---

## 🛡️ Firewall Setup

```bash
# Install UFW
apt-get install -y ufw

# Allow SSH, HTTP, HTTPS
ufw allow 22
ufw allow 80
ufw allow 443

# Enable firewall
ufw enable

# Check status
ufw status
```

---

## 💾 Database Backup

### Create backup:
```bash
cd /opt/xbooking/Xbooking
docker-compose exec db pg_dump -U xbooking_user xbooking > backup_$(date +%Y%m%d).sql
```

### Restore backup:
```bash
docker-compose exec -T db psql -U xbooking_user xbooking < backup_20231128.sql
```

---

## 🔍 Troubleshooting

### Check if all services are running:
```bash
docker-compose ps
```

All services should show `Up` status.

### Web service not starting:
```bash
docker-compose logs web
```
- Check for missing environment variables
- Verify database connection

### SSL certificate issues:
```bash
docker-compose logs certbot
```
- Ensure DNS is properly configured
- Check if domain points to server IP

### Celery not processing tasks:
```bash
docker-compose logs celery_worker
```
- Check Redis connection
- Verify CELERY_BROKER_URL in .env.production

### Database connection refused:
```bash
docker-compose logs db
```
- Wait for database to be healthy
- Check POSTGRES_PASSWORD matches

---

## 📊 Architecture Diagram

```
                     Internet
                        │
                        ▼
              ┌─────────────────┐
              │     Nginx       │ ← Port 80/443 (SSL)
              │  (Reverse Proxy)│
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │     Django      │ ← Port 8000
              │   (Gunicorn)    │
              └────────┬────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
    ▼                  ▼                  ▼
┌─────────┐      ┌──────────┐      ┌───────────┐
│PostgreSQL│      │  Redis   │      │  Celery   │
│(Database)│      │ (Broker) │      │(Worker +  │
│          │      │          │      │   Beat)   │
└─────────┘      └──────────┘      └───────────┘
```

---

## 💰 VPS Cost Comparison

| Provider | Plan | RAM | CPU | Storage | Price |
|----------|------|-----|-----|---------|-------|
| **Hetzner** | CX11 | 2GB | 1 | 20GB | €3.29/mo |
| **Vultr** | Cloud | 1GB | 1 | 25GB | $5/mo |
| **Linode** | Nanode | 1GB | 1 | 25GB | $5/mo |
| **DigitalOcean** | Basic | 1GB | 1 | 25GB | $6/mo |

**Recommendation**: Start with 1GB RAM, upgrade to 2GB for better Celery performance.

---

## ✅ Deployment Checklist

- [ ] DNS configured (domain points to server IP)
- [ ] SSH access to server
- [ ] `.env.production` configured with real values
- [ ] `SECRET_KEY` is a strong random string
- [ ] `POSTGRES_PASSWORD` is strong
- [ ] Email credentials configured
- [ ] Payment gateway keys configured
- [ ] Webhook URLs set in Paystack/Flutterwave dashboards
- [ ] Frontend API URL updated
- [ ] Firewall enabled (ports 22, 80, 443)
- [ ] Superuser created for admin panel
- [ ] Test API endpoints working
- [ ] Test payment flow working

---

## 🆘 Support

If you encounter issues:
1. Check logs: `docker-compose logs -f`
2. Verify all services running: `docker-compose ps`
3. Ensure environment variables are correct
4. Check DNS propagation: `dig yourdomain.com`

