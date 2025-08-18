# XBooking Backend API

<div align="center">
  <img src="https://xbooking.netlify.app/xbookinglogonew1.png" alt="XBooking Logo" width="200"/>
  
  **An innovative new platform for discovering and booking premium workspaces**
  
  ![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
  ![Django](https://img.shields.io/badge/Django-4.0+-green.svg)
  ![DRF](https://img.shields.io/badge/DRF-3.14+-orange.svg)
  ![JWT](https://img.shields.io/badge/JWT-Authentication-red.svg)
  ![License](https://img.shields.io/badge/License-MIT-yellow.svg)
</div>

## 🚀 About XBooking

XBooking is an innovative new workspace booking platform that connects professionals with premium workspaces across 50+ cities worldwide. Our backend API powers the seamless booking experience, from instant workspace discovery to secure payment processing.

**Live Platform**: [https://xbooking.netlify.app/](https://xbooking.netlify.app/)

### 🎯 Mission
To democratize access to premium workspaces and empower professionals to work from anywhere, creating a more flexible and productive future of work.

### 🔮 Vision  
To become the global platform that connects every professional with their perfect workspace, making flexible work the new standard across all industries.

## ✨ Features

### 🔐 Authentication & User Management
- **JWT-based Authentication** - Secure token-based auth system
- **User Registration & Login** - Email-based authentication with password validation
- **Profile Management** - Complete user profile system with avatar generation
- **Password Reset** - Secure password reset with email verification codes
- **Admin Dashboard** - Enhanced admin interface with user management

### 🏢 Workspace Management (Coming Soon)
- **Instant Booking** - Real-time workspace availability and booking
- **AI-Powered Matching** - Personalized workspace recommendations
- **Global Network** - Premium workspaces in 50+ cities
- **Usage Analytics** - Track workspace usage patterns

### 💳 Payment Integration (Coming Soon)
- **Secure Payments** - Paystack and Flutterwave integration
- **Multiple Payment Options** - Cards, bank transfers, mobile money
- **Invoice Generation** - Automated billing and receipts

### 📱 API Features
- **RESTful API** - Clean, well-documented endpoints
- **Interactive Documentation** - Built-in API testing interface
- **Mobile-First** - Optimized for mobile applications
- **Real-time Updates** - WebSocket support for live data

## 🛠️ Technology Stack

### Backend Framework
- **Django 4.0+** - High-level Python web framework
- **Django REST Framework** - Powerful toolkit for building APIs
- **PostgreSQL/SQLite** - Robust database systems
- **Celery** - Distributed task queue for background jobs

### Authentication & Security
- **JWT (Simple JWT)** - JSON Web Token authentication
- **PBKDF2** - Secure password hashing
- **CORS** - Cross-Origin Resource Sharing support
- **Rate Limiting** - API throttling and protection

### External Integrations
- **DiceBear API** - Automated avatar generation
- **Email Services** - SMTP/SendGrid for notifications
- **Paystack & Flutterwave** - Payment processing (coming soon)
- **AWS S3** - File storage and media handling (coming soon)

### Development Tools
- **Poetry/pip** - Dependency management
- **Black** - Code formatting
- **Flake8** - Code linting
- **Pytest** - Testing framework
- **Docker** - Containerization (coming soon)

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip or Poetry
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/shoileazeez/Xbooking_backend.git
   cd Xbooking_backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   cd Xbooking
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the server**
   ```bash
   python manage.py runserver
   ```

8. **Access the API**
   - API Documentation: `http://localhost:8000/`
   - Admin Panel: `http://localhost:8000/admin/`
   - API Endpoints: `http://localhost:8000/api/`

## 📚 API Documentation

### Interactive Documentation
Visit `http://localhost:8000/` for the interactive API documentation with live testing capabilities.

### Authentication Endpoints

#### User Registration
```http
POST /api/user/register/
Content-Type: application/json

{
  "full_name": "John Doe",
  "email": "john.doe@example.com", 
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
```

#### User Login
```http
POST /api/user/login/
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "password": "SecurePass123!"
}
```

#### Password Reset Request
```http
POST /api/user/password-reset/
Content-Type: application/json

{
  "email": "john.doe@example.com"
}
```

#### Password Reset Confirm
```http
POST /api/user/password-reset-confirm/
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "verification_code": "123456",
  "new_password": "NewSecurePass123!"
}
```

### Response Format
All API responses follow this structure:
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    // Response data
  },
  "errors": null
}
```

## 🧪 Testing

### Run All Tests
```bash
python manage.py test
```

### Run Specific Test Suites
```bash
# User authentication tests
python manage.py test user.tests

# Registration tests only
python manage.py test user.tests.registration

# Login tests only  
python manage.py test user.tests.login
```

### Test Coverage
```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

### Custom Test Runner
```bash
# Run organized test suites
python run_tests.py
```

## 📁 Project Structure

```
Xbooking_backend/
├── Xbooking/                 # Django project root
│   ├── manage.py             # Django management script
│   ├── run_tests.py          # Custom test runner
│   ├── templates/            # Global templates
│   │   └── index.html        # API documentation page
│   ├── Xbooking/            # Project settings
│   │   ├── __init__.py
│   │   ├── settings.py       # Django settings
│   │   ├── urls.py          # Main URL configuration
│   │   └── wsgi.py          # WSGI configuration
│   └── user/                # User authentication app
│       ├── models.py        # User model and database schema
│       ├── serializers/     # API serializers
│       ├── validators/      # Data validation logic
│       ├── views/          # API endpoints
│       ├── admin.py        # Admin interface customization
│       ├── tests/          # Comprehensive test suite
│       └── README.md       # User app documentation
├── venv/                   # Virtual environment
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL for production)
DATABASE_URL=postgresql://user:password@localhost:5432/xbooking

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# JWT Settings
JWT_ACCESS_TOKEN_LIFETIME=60  # minutes
JWT_REFRESH_TOKEN_LIFETIME=7  # days

# External APIs
DICEBEAR_API_URL=https://api.dicebear.com/7.x/initials/svg

# Payment Gateways (Coming Soon)
PAYSTACK_SECRET_KEY=your-paystack-secret
FLUTTERWAVE_SECRET_KEY=your-flutterwave-secret
```

### Database Configuration

#### SQLite (Development)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

#### PostgreSQL (Production)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'xbooking',
        'USER': 'your-user',
        'PASSWORD': 'your-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG = False`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Use PostgreSQL database
- [ ] Set up Redis for caching
- [ ] Configure email backend
- [ ] Set up media file storage (AWS S3)
- [ ] Enable HTTPS
- [ ] Set up monitoring and logging

### Docker Deployment (Coming Soon)
```bash
docker build -t xbooking-backend .
docker run -p 8000:8000 xbooking-backend
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`python manage.py test`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Style
- Follow PEP 8 guidelines
- Use Black for code formatting
- Add docstrings to all functions and classes
- Write comprehensive tests

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

### Get Help
- **Documentation**: [API Docs](http://localhost:8000/)
- **Email**: [hello@xbooking.com](mailto:hello@xbooking.com)
- **Issues**: [GitHub Issues](https://github.com/shoileazeez/Xbooking_backend/issues)

### Quick Links
- **Platform**: [https://xbooking.netlify.app/](https://xbooking.netlify.app/)
- **Find Spaces**: [https://xbooking.netlify.app/search](https://xbooking.netlify.app/search)
- **List Your Space**: [https://xbooking.netlify.app/list-space](https://xbooking.netlify.app/list-space)
- **Enterprise**: [https://xbooking.netlify.app/enterprise](https://xbooking.netlify.app/enterprise)

## 🙏 Acknowledgments

- Django and DRF communities for excellent frameworks
- DiceBear for avatar generation API
- All contributors and testers
- Open source community

---

<div align="center">
  <p><strong>Built with ❤️ by the XBooking Team</strong></p>
  <p>© 2024 XBooking. All rights reserved.</p>
</div>