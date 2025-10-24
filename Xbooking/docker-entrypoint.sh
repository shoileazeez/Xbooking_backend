#!/bin/bash
set -e

echo "Starting Xbooking application..."

# Wait for the database to be ready (if using PostgreSQL)
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database to be ready..."
    # Extract host and port from DATABASE_URL if needed
    # For now, we'll add a simple sleep
    sleep 2
fi

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting Gunicorn server..."
# Execute the main command (passed as arguments to this script)
exec "$@"
