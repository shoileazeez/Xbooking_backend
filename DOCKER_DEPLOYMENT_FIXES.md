# Docker Deployment Fixes

This document describes the changes made to fix Docker deployment issues.

## Issues Fixed

1. **SQLite Error during Docker build**: Migrations were running during the Docker build phase when the database file couldn't be created (permission issues with non-root user)
2. **collectstatic command not found**: The `django.contrib.staticfiles` app was missing from INSTALLED_APPS
3. **UTF-16 encoding in requirements.txt**: The requirements file was encoded as UTF-16 which could cause issues in some environments

## Changes Made

### 1. Django Settings (`Xbooking/settings.py`)
- Added `django.contrib.staticfiles` to `INSTALLED_APPS`
- Added `whitenoise.middleware.WhiteNoiseMiddleware` to `MIDDLEWARE` for serving static files in production
- Added static files configuration:
  ```python
  STATIC_URL = '/static/'
  STATIC_ROOT = BASE_DIR / 'staticfiles'
  MEDIA_URL = '/media/'
  MEDIA_ROOT = BASE_DIR / 'media'
  ```

### 2. Dockerfile (`Xbooking/Dockerfile`)
- Removed migration and collectstatic commands from build stage
- Created directories for static and media files with proper permissions
- Changed the order: create user and set permissions before switching to non-root user
- Added ENTRYPOINT to use `docker-entrypoint.sh` script

### 3. Entrypoint Script (`Xbooking/docker-entrypoint.sh`)
- Created new entrypoint script that runs at container startup
- Migrations now run when container starts (not during build)
- Collectstatic runs when container starts (not during build)
- This ensures database is available when migrations run

### 4. Requirements File (`Xbooking/requirements.txt`)
- Converted from UTF-16 to UTF-8 encoding for better compatibility

### 5. Git Ignore (`.gitignore`)
- Added `staticfiles/` and `media/` to prevent committing generated files

## How It Works Now

1. **Build Phase**: 
   - Install system dependencies
   - Install Python packages
   - Copy application code
   - Create user and set permissions
   - NO migrations or collectstatic

2. **Runtime Phase** (when container starts):
   - Entrypoint script runs
   - Migrations execute (database should be ready)
   - Static files collected
   - Gunicorn server starts

## Benefits

- ✅ Build works without requiring database connection
- ✅ Non-root user has proper permissions
- ✅ Migrations run at appropriate time (runtime, not build time)
- ✅ Static files properly configured and collected
- ✅ Better separation of build and runtime concerns

## Testing

To test locally:
```bash
cd Xbooking
docker build -t xbooking:latest .
docker run -p 8000:8000 xbooking:latest
```

For production with PostgreSQL:
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/dbname" \
  xbooking:latest
```
