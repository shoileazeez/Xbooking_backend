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
    # Expire booking QR codes every hour (when checkout time is passed)
    'expire-booking-qr-codes': {
        'task': 'qr_code.tasks.expire_booking_qr_codes',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    # Send booking reminders 1 hour before check-in (checks every hour)
    'send-booking-reminders': {
        'task': 'qr_code.tasks.send_upcoming_booking_reminders',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    # Check and send guest check-in reminders (1 hour before check-in)
    'send-guest-checkin-reminders': {
        'task': 'booking.guest_tasks.check_and_send_guest_reminders',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    # Check and send checkout receipts to guests who have checked out
    'send-guest-checkout-receipts': {
        'task': 'booking.guest_tasks.check_and_send_checkout_receipts',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
