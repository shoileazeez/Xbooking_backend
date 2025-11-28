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

RUN python manage.py collectstatic --noinput --clear || echo "Static collection failed, continuing..."

# Expose port
EXPOSE 8000

# Default command for web service (override in render.yaml for workers)
CMD ["bash", "-c", "python manage.py migrate --noinput && python manage.py populate_workspace_data && gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 Xbooking.wsgi:application"]

