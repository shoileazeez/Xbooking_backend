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

# Explicitly import tasks from non-standard task files
app.autodiscover_tasks(['booking'], related_name='guest_tasks')

# Celery Beat Schedule - for periodic tasks
app.conf.beat_schedule = {
    # Expire old QR codes every hour
    'expire-old-qr-codes': {
        'task': 'qr_code.tasks.expire_old_qr_codes',
        'schedule': crontab(minute=0),  # Every hour
    },
    # Expire old booking QR codes every hour
    'expire-booking-qr-codes': {
        'task': 'qr_code.tasks.expire_booking_qr_codes',
        'schedule': crontab(minute=0),  # Every hour
    },
    # Send booking reminders 1 hour before check-in (checks every hour)
    'send-booking-reminders': {
        'task': 'qr_code.tasks.send_upcoming_booking_reminders',
        'schedule': crontab(minute=0),  # Every hour
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
