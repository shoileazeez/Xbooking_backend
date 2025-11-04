# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=Xbooking.settings

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN addgroup --system django \
    && adduser --system --ingroup django django

RUN mkdir -p /app && chmod -R 777 /app

# Copy requirements file first (for better caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/


# Switch to non-root user
USER django

RUN python manage.py collectstatic --noinput --clear || echo "Static collection failed, continuing..."

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import django; django.setup(); from django.http import HttpRequest; from django.test import Client; client = Client(); response = client.get('/'); assert response.status_code in [200, 301, 302]" || exit 1

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["bash", "-c", "python manage.py migrate --noinput && gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 Xbooking.wsgi:application"]

