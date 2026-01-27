#!/bin/bash
# Start Celery Beat for scheduled tasks
echo "Starting Celery Beat..."
cd "$(dirname "$0")"
celery -A Xbooking beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
