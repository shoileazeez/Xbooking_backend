# XBooking Backend API

<div align="center">
  
  ![XBooking](https://img.shields.io/badge/XBooking-Professional%20Workspace%20Booking-blue?style=for-the-badge)
  
  **Enterprise-grade workspace booking platform built with Django & REST Framework**
  
  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg?style=flat-square)](https://python.org)
  [![Django](https://img.shields.io/badge/Django-5.2+-green.svg?style=flat-square)](https://djangoproject.com)
  [![DRF](https://img.shields.io/badge/DRF-3.14+-orange.svg?style=flat-square)](https://www.django-rest-framework.org)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg?style=flat-square)](https://postgresql.org)
  [![JWT](https://img.shields.io/badge/JWT-Secure%20Auth-red.svg?style=flat-square)](https://jwt.io)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
  [![API Docs](https://img.shields.io/badge/API-Documented-brightgreen.svg?style=flat-square)](http://localhost:8000)
  
</div>

---

## 📋 Table of Contents

- [About](#about)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Support](#support)
- [License](#license)

---

## 🚀 About

**XBooking** is an enterprise-grade workspace booking platform that connects professionals with premium workspaces across multiple cities. Built with Django and Django REST Framework, it provides a robust, scalable backend for managing workspace bookings, payments, user management, and workspace administration.

### 🎯 Mission
Democratize access to premium workspaces and empower professionals to work from anywhere, creating a more flexible and productive future of work.

### Platform
- **Frontend**: [https://xbooking.netlify.app/](https://xbooking.netlify.app/)
- **API Docs**: Available at `/` when running locally

---

## ✨ Features

### 🔐 **Authentication & User Management**
- **JWT-based Authentication** - Secure, scalable token authentication
- **Email-based Registration** - Password validation and strength checking
- **User Profiles** - Complete profile system with avatar generation via DiceBear API
- **Password Management** - Secure reset with verification codes
- **Admin Controls** - Forced password changes, access revocation/restoration
- **User Status Tracking** - Active/inactive user management
- **UUID Primary Keys** - Secure user identification system

### 🏢 **Workspace Management**
- **Workspace Creation** - Setup and configure workspaces
- **Space Management** - Manage individual spaces within workspaces
- **Workspace Memberships** - User roles and permissions (Owner, Manager, Member)
- **Workspace Invitations** - Invite users to workspaces
- **Space Availability** - Real-time availability tracking

### 📅 **Booking System**
- **Shopping Cart** - Add/remove spaces to cart before checkout
- **Instant Booking** - One-click booking with real-time availability
- **Booking Management** - View, cancel, and modify bookings
- **Booking Reviews** - User reviews and ratings system
- **Booking History** - Track all historical bookings

### 👥 **Guest Management**
- **Guest Addition** - Add guests (coworkers, friends, family) to bookings
- **Admin Verification** - Two-stage verification system for guests
- **QR Code Generation** - Unique verification codes for check-in
- **Per-Booking Verification** - Admin verification scoped to individual bookings
- **Guest Tracking** - Track guest status and check-in/check-out
- **Email Notifications** - Automated guest notifications with QR codes

### 💳 **Payment Integration**
- **Paystack Integration** - Accept card and mobile money payments
- **Flutterwave Integration** - Multiple payment methods support
- **Payment Processing** - Secure payment handling and PCI compliance
- **Refund Management** - Process refunds with audit trail
- **Payment Webhooks** - Handle payment callbacks and updates
- **Order Management** - Order creation and tracking

### 💰 **Withdrawal/Payout System**
- **Bank Accounts** - Multiple account support with default selection
- **Withdrawal Requests** - Create and manage withdrawal requests
- **Approval Workflow** - Admin approval system for payouts
- **Payout Processing** - Automated payout with Celery tasks
- **Audit Trail** - Complete withdrawal history logging
- **Status Tracking** - Pending, approved, processing, completed states

### 🔔 **Notification System**
- **Email Notifications** - Automated email alerts via SMTP
- **SMS Notifications** - SMS alerts for critical events (coming soon)
- **In-App Notifications** - Real-time in-app messaging
- **Notification Preferences** - User-configurable notification settings
- **Event Triggers** - Automated notifications for bookings, payments, reviews

### 🎯 **Other Features**
- **QR Code System** - Generate and verify QR codes for check-in
- **API Documentation** - Interactive Swagger/ReDoc documentation
- **Error Handling** - Comprehensive error messages and logging
- **Rate Limiting** - API throttling for protection
- **CORS Support** - Cross-origin request handling
- **Data Validation** - Comprehensive input validation

---

## 🛠️ Technology Stack

### Backend Framework
| Technology | Purpose |
|-----------|---------|
| **Django 5.2** | Web framework |
| **Django REST Framework** | API development |
| **drf-spectacular** | OpenAPI schema generation |
| **Simple JWT** | JWT authentication |

### Database & Caching
| Technology | Purpose |
|-----------|---------|
| **PostgreSQL 15+** | Primary database (production) |
| **SQLite 3** | Development database |
| **Redis** | Caching and Celery broker |
| **django-redis** | Redis cache backend |

### Background Tasks & Jobs
| Technology | Purpose |
|-----------|---------|
| **Celery** | Distributed task queue |
| **Redis** | Message broker |
| **QR Code** | QR code generation |

### Security & Authentication
| Technology | Purpose |
|-----------|---------|
| **PBKDF2** | Password hashing |
| **JWT (JSON Web Tokens)** | API authentication |
| **CORS Headers** | Cross-origin support |
| **SSL/TLS** | HTTPS support |

### External Integrations
| Service | Purpose |
|---------|---------|
| **DiceBear API** | Avatar generation |
| **Paystack** | Payment processing |
| **Flutterwave** | Payment processing |
| **SMTP/Mailjet** | Email delivery |

---

## 🚀 Quick Start

### Prerequisites
```
✓ Python 3.12 or higher
✓ Git
✓ pip
✓ PostgreSQL 15+ (optional, SQLite works for development)
✓ Redis (optional, for background tasks)
```

### Installation Steps

#### 1. Clone Repository
```bash
git clone https://github.com/shoileazeez/Xbooking_backend.git
cd Xbooking_backend
```

#### 2. Create Virtual Environment
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Environment Configuration
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
```

#### 5. Database Setup
```bash
cd Xbooking

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser (admin account)
python manage.py createsuperuser
```

#### 6. Run Development Server
```bash
python manage.py runserver
```

#### 7. Access the Application

| Service | URL |
|---------|-----|
| **API Root** | http://localhost:8000/ |
| **API Documentation** | http://localhost:8000/schema/ |
| **Admin Dashboard** | http://localhost:8000/admin/ |

---

## 📚 API Documentation

### Core Endpoints

#### User Registration
```http
POST /api/user/register/
Content-Type: application/json

{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "confirm_password": "SecurePassword123!"
}
```

#### User Login
```http
POST /api/user/login/
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

#### Get User Profile
```http
GET /api/user/profile/
Authorization: Bearer {access_token}
```

#### Add Guest to Booking
```http
POST /api/booking/workspaces/{workspace_id}/bookings/{booking_id}/guests/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane@example.com",
  "phone": "+234812345678"
}
```

---

## 📁 Project Structure

```
Xbooking_backend/
├── Xbooking/                           # Django Project Root
│   ├── manage.py                       # Django CLI
│   ├── Xbooking/                       # Project Configuration
│   │   ├── settings.py                 # Django settings
│   │   ├── urls.py                     # Main URL routing
│   │   └── celery.py                   # Celery config
│   ├── user/                           # User Authentication
│   │   ├── models.py                   # User model
│   │   ├── views/                      # API views
│   │   ├── authentication.py           # Custom JWT auth
│   │   └── urls.py                     # URL routing
│   ├── workspace/                      # Workspace Management
│   ├── booking/                        # Booking System
│   ├── payment/                        # Payment Integration
│   ├── qr_code/                        # QR Code System
│   └── notifications/                  # Notifications
├── venv/                               # Virtual environment
├── requirements.txt                    # Dependencies
├── .env.example                        # Environment template
└── README.md                           # Documentation
```

---

## 🔧 Configuration

### Environment Variables

```env
# Django Core
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/xbooking

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password

# JWT
ACCESS_TOKEN_LIFETIME_MINUTES=30
REFRESH_TOKEN_LIFETIME_DAYS=1

# Celery & Redis
CELERY_BROKER_URL=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/1

# Payment Gateways
PAYSTACK_SECRET_KEY=sk_test_...
PAYSTACK_PUBLIC_KEY=pk_test_...
FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST_...
```

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test user

# With coverage
coverage run --source='.' manage.py test
coverage report
```

---

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG = False`
- [ ] Generate new `SECRET_KEY`
- [ ] Set proper `ALLOWED_HOSTS`
- [ ] Configure PostgreSQL
- [ ] Set up Redis
- [ ] Configure email backend
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring

### Using Gunicorn
```bash
gunicorn Xbooking.wsgi:application --bind 0.0.0.0:8000
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run tests: `python manage.py test`
5. Commit: `git commit -m 'Add feature'`
6. Push: `git push origin feature/amazing-feature`
7. Create Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details

---

## 📞 Support

- **Documentation**: [API Docs](http://localhost:8000/)
- **Email**: [support@xbooking.com](mailto:support@xbooking.com)
- **GitHub Issues**: [Report Bugs](https://github.com/shoileazeez/Xbooking_backend/issues)

---

<div align="center">
  
### Made with ❤️ by the XBooking Team

**© 2024 XBooking. All rights reserved.**

</div>
