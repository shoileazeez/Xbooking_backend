"""
Celery configuration for Xbooking project
"""
import os
import sys
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')

app = Celery('Xbooking')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Windows-specific configuration - use solo pool to avoid multiprocessing issues
if sys.platform == 'win32':
    app.conf.worker_pool = 'solo'
    # Disable prefork on Windows
    app.conf.worker_pool_restarts = True

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

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
        'task': 'booking.tasks.check_and_send_guest_reminders',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    # Check and send checkout receipts to guests who have checked out
    'send-guest-checkout-receipts': {
        'task': 'booking.tasks.check_and_send_checkout_receipts',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    # Expire active reservations that have passed their expiry time
    'expire-reservations': {
        'task': 'booking.tasks.expire_reservations',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    },
    # Send expiry warnings for reservations expiring in 2 minutes
    'send-reservation-expiry-warnings': {
        'task': 'booking.tasks.send_reservation_expiry_warning',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    },
    # Clean up old expired/cancelled reservations (daily)
    'clean-old-reservations': {
        'task': 'booking.tasks.clean_old_reservations',
        'schedule': crontab(hour='0', minute='0'),  # Daily at midnight
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
