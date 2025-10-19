"""
Celery configuration for Xbooking project
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')

app = Celery('Xbooking')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Celery Beat Schedule - for periodic tasks
app.conf.beat_schedule = {
    # Expire old QR codes every hour
    'expire-old-qr-codes': {
        'task': 'qr_code.tasks.expire_old_qr_codes',
        'schedule': crontab(minute=0),  # Every hour
    },
    # Send booking reminders 1 hour before check-in
    'send-booking-reminders': {
        'task': 'qr_code.tasks.send_booking_reminder',
        'schedule': crontab(minute=0),  # Every hour
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
