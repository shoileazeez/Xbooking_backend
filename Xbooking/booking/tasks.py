"""
Celery tasks for booking reservation management
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name='booking.tasks.expire_reservations')
def expire_reservations():
    """
    Expire old reservations that haven't been confirmed.
    Runs every 2 minutes to check for expired reservations.
    """
    from booking.models import Reservation, CartItem
    
    now = timezone.now()
    
    # Find active reservations that have expired
    expired_reservations = Reservation.objects.filter(
        status='active',
        expires_at__lte=now
    ).select_related('space', 'user')
    
    count = 0
    for reservation in expired_reservations:
        # Mark reservation as expired
        reservation.expire()
        
        # Reset slots back to available
        from workspace.models import SpaceCalendarSlot
        SpaceCalendarSlot.objects.filter(
            calendar__space=reservation.space,
            date__gte=reservation.start.date(),
            date__lte=reservation.end.date(),
            status='reserved'
        ).update(status='available')
        
        # Remove associated cart items
        CartItem.objects.filter(reservation=reservation).delete()
        
        logger.info(
            f"Expired reservation {reservation.id} for {reservation.space.name} "
            f"by {reservation.user.email} - slots reset to available"
        )
        count += 1
    
    if count > 0:
        logger.info(f"Expired {count} reservation(s)")
    
    return {
        'expired_count': count,
        'timestamp': now.isoformat()
    }


@shared_task(name='booking.tasks.clean_old_reservations')
def clean_old_reservations():
    """
    Clean up old expired reservations (older than 24 hours).
    Runs daily to keep database clean.
    """
    from booking.models import Reservation
    
    cutoff = timezone.now() - timedelta(hours=24)
    
    # Delete old expired/cancelled reservations
    deleted_count, _ = Reservation.objects.filter(
        status__in=['expired', 'cancelled'],
        updated_at__lt=cutoff
    ).delete()
    
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old reservation(s)")
    
    return {
        'deleted_count': deleted_count,
        'cutoff': cutoff.isoformat()
    }


@shared_task(name='booking.tasks.send_reservation_expiry_warning')
def send_reservation_expiry_warning():
    """
    Send warnings to users whose reservations are about to expire (2 minutes left).
    """
    from booking.models import Reservation
    from core.services import EventBus, Event
    
    now = timezone.now()
    warning_time = now + timedelta(minutes=2)
    
    # Find reservations expiring in next 2 minutes
    expiring_soon = Reservation.objects.filter(
        status='active',
        expires_at__lte=warning_time,
        expires_at__gt=now
    ).select_related('space', 'user')
    
    for reservation in expiring_soon:
        # Publish expiry warning event
        event = Event(
            event_type='RESERVATION_EXPIRING',
            data={
                'reservation_id': str(reservation.id),
                'user_id': str(reservation.user.id),
                'user_email': reservation.user.email,
                'space_id': str(reservation.space.id),
                'space_name': reservation.space.name,
                'expires_at': reservation.expires_at.isoformat(),
                'minutes_remaining': int((reservation.expires_at - now).total_seconds() / 60),
                'timestamp': now.isoformat()
            },
            source_module='booking'
        )
        EventBus.publish(event)
        
        logger.info(
            f"Sent expiry warning for reservation {reservation.id} "
            f"to {reservation.user.email}"
        )
    
    return {
        'warnings_sent': expiring_soon.count(),
        'timestamp': now.isoformat()
    }


@shared_task
def generate_guest_qr_code(guest_id):
    """Generate QR code for a guest"""
    try:
        from booking.models import Guest
        from Xbooking.cloudinary_storage import upload_qr_image_to_cloudinary
        import qrcode
        import io
        
        guest = Guest.objects.select_related('booking', 'booking__space', 'booking__user').get(id=guest_id)
        
        # QR code data
        qr_data = f"https://app.xbooking.dev/guest/verify/{guest.qr_code_verification_code}"
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        qr_image_bytes = img_io.getvalue()
        
        # Upload to Cloudinary
        filename = f"qr_guest_{guest.id}_{guest.qr_code_verification_code}.png"
        cloud_result = upload_qr_image_to_cloudinary(qr_image_bytes, filename, public_id=f"qr_guest_{guest.qr_code_verification_code}")
        
        # Send QR code email
        if cloud_result.get('success'):
            qr_code_url = cloud_result.get('file_url')
            send_guest_qr_email.delay(str(guest.id), qr_code_url, qr_data)
        
        return {'success': True, 'guest_id': str(guest.id), 'qr_url': cloud_result.get('file_url')}
    except Exception as e:
        logger.error(f"Failed to generate guest QR code for {guest_id}: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_guest_qr_email(guest_id, qr_code_url, qr_data):
    """Send guest QR code via email"""
    try:
        from booking.models import Guest
        from django.template.loader import render_to_string
        from Xbooking.mailjet_utils import send_mailjet_email
        from django.conf import settings
        import requests
        import base64
        
        guest = Guest.objects.select_related('booking', 'booking__space', 'booking__workspace').get(id=guest_id)
        booking = guest.booking
        
        context = {
            'guest_name': f"{guest.first_name} {guest.last_name}",
            'booker_name': booking.user.full_name or booking.user.email,
            'space_name': booking.space.name,
            'workspace_name': booking.workspace.name,
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'qr_code_url': qr_code_url,
            'verification_code': guest.qr_code_verification_code,
        }
        
        html_content = render_to_string('emails/guest_qr_code.html', context)
        text_content = render_to_string('emails/guest_qr_code.txt', context)
        
        # Attach QR code image
        attachments = []
        try:
            resp = requests.get(qr_code_url, timeout=15)
            if resp.status_code == 200:
                attachments.append({
                    'ContentType': 'image/png',
                    'Filename': f'guest_qr_{guest.qr_code_verification_code}.png',
                    'Base64Content': base64.b64encode(resp.content).decode('utf-8')
                })
        except Exception as e:
            logger.warning(f"Failed to attach QR image: {str(e)}")
        
        result = send_mailjet_email(
            subject=f'Your Guest QR Code for {booking.space.name}',
            to_email=guest.email,
            to_name=f"{guest.first_name} {guest.last_name}",
            html_content=html_content,
            text_content=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            from_name='XBooking',
            attachments=attachments
        )
        
        if result.get('success'):
            guest.qr_code_sent = True
            guest.qr_code_sent_at = timezone.now()
            guest.save(update_fields=['qr_code_sent', 'qr_code_sent_at'])
        
        return result
    except Exception as e:
        logger.error(f"Failed to send guest QR email for {guest_id}: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_guest_check_in_reminder(guest_id):
    """Send check-in reminder to guest"""
    try:
        from booking.models import Guest
        from django.template.loader import render_to_string
        from Xbooking.mailjet_utils import send_mailjet_email
        from django.conf import settings
        
        guest = Guest.objects.select_related('booking', 'booking__space', 'booking__workspace').get(id=guest_id)
        booking = guest.booking
        
        context = {
            'guest_name': f"{guest.first_name} {guest.last_name}",
            'space_name': booking.space.name,
            'workspace_name': booking.workspace.name,
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'verification_code': guest.qr_code_verification_code,
        }
        
        html_content = render_to_string('emails/guest_check_in_reminder.html', context)
        text_content = render_to_string('emails/guest_check_in_reminder.txt', context)
        
        result = send_mailjet_email(
            subject=f'Reminder: Check-in at {booking.space.name} Today',
            to_email=guest.email,
            to_name=f"{guest.first_name} {guest.last_name}",
            html_content=html_content,
            text_content=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            from_name='XBooking'
        )
        
        if result.get('success'):
            guest.reminder_sent = True
            guest.reminder_sent_at = timezone.now()
            guest.save(update_fields=['reminder_sent', 'reminder_sent_at'])
        
        return result
    except Exception as e:
        logger.error(f"Failed to send guest reminder for {guest_id}: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_guest_checkout_receipt(guest_id):
    """Send checkout receipt to guest"""
    try:
        from booking.models import Guest
        from django.template.loader import render_to_string
        from Xbooking.mailjet_utils import send_mailjet_email
        from django.conf import settings
        
        guest = Guest.objects.select_related('booking', 'booking__space', 'booking__workspace').get(id=guest_id)
        booking = guest.booking
        
        context = {
            'guest_name': f"{guest.first_name} {guest.last_name}",
            'space_name': booking.space.name,
            'workspace_name': booking.workspace.name,
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'checked_in_at': guest.checked_in_at,
            'checked_out_at': guest.checked_out_at,
        }
        
        html_content = render_to_string('emails/guest_checkout_receipt.html', context)
        text_content = render_to_string('emails/guest_checkout_receipt.txt', context)
        
        result = send_mailjet_email(
            subject=f'Thank you for visiting {booking.space.name}',
            to_email=guest.email,
            to_name=f"{guest.first_name} {guest.last_name}",
            html_content=html_content,
            text_content=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            from_name='XBooking'
        )
        
        if result.get('success'):
            guest.receipt_sent = True
            guest.receipt_sent_at = timezone.now()
            guest.save(update_fields=['receipt_sent', 'receipt_sent_at'])
        
        return result
    except Exception as e:
        logger.error(f"Failed to send guest receipt for {guest_id}: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task(name='booking.tasks.check_and_send_guest_reminders')
def check_and_send_guest_reminders():
    """Check for guests with bookings starting in 1 hour and send reminders"""
    try:
        from booking.models import Guest
        
        now = timezone.now()
        one_hour_later = now + timedelta(hours=1)
        
        guests_needing_reminders = Guest.objects.filter(
            booking__status='confirmed',
            booking__check_in__gte=now,
            booking__check_in__lte=one_hour_later,
            reminder_sent=False,
            qr_code_sent=True
        ).select_related('booking')
        
        sent_count = 0
        for guest in guests_needing_reminders:
            send_guest_check_in_reminder.delay(str(guest.id))
            sent_count += 1
        
        return {'success': True, 'reminders_queued': sent_count}
    except Exception as e:
        logger.error(f"Failed to check guest reminders: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task(name='booking.tasks.check_and_send_checkout_receipts')
def check_and_send_checkout_receipts():
    """Check for guests who have checked out and send receipts"""
    try:
        from booking.models import Guest
        
        guests_needing_receipts = Guest.objects.filter(
            status='checked_out',
            receipt_sent=False,
            checked_out_at__isnull=False
        ).select_related('booking')
        
        sent_count = 0
        for guest in guests_needing_receipts:
            send_guest_checkout_receipt.delay(str(guest.id))
            sent_count += 1
        
        return {'success': True, 'receipts_queued': sent_count}
    except Exception as e:
        logger.error(f"Failed to check guest receipts: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def generate_guest_qr_codes_for_booking(booking_id):
    """Generate QR codes for all guests in a booking"""
    try:
        from booking.models import Booking, Guest
        
        booking = Booking.objects.get(id=booking_id)
        guests = Guest.objects.filter(booking=booking)
        
        generated_count = 0
        for guest in guests:
            generate_guest_qr_code.delay(str(guest.id))
            generated_count += 1
        
        return {'success': True, 'guests_count': generated_count}
    except Exception as e:
        logger.error(f"Failed to generate guest QR codes for booking {booking_id}: {str(e)}")
        return {'success': False, 'error': str(e)}


__all__ = [
    'expire_reservations',
    'clean_old_reservations',
    'send_reservation_expiry_warning',
    'generate_guest_qr_code',
    'send_guest_qr_email',
    'send_guest_check_in_reminder',
    'send_guest_checkout_receipt',
    'check_and_send_guest_reminders',
    'check_and_send_checkout_receipts',
    'generate_guest_qr_codes_for_booking',
]
