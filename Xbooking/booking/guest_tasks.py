"""
Celery tasks for Guest Management
"""
from celery import shared_task
from django.utils import timezone
from booking.models import Booking, Guest
import logging
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_guest_qr_code_email(self, guest_id, booking_id):
    """
    Send QR code email to guest
    Generates QR code with verification code and sends to guest email
    """
    try:
        guest = Guest.objects.get(id=guest_id)
        booking = Booking.objects.get(id=booking_id)
        
        logger.info(f"Generating QR code for guest {guest.id}: {guest.email}")
        
        # Generate QR code data
        qr_data = {
            'guest_id': str(guest.id),
            'verification_code': guest.qr_code_verification_code,
            'guest_name': f"{guest.first_name} {guest.last_name}",
            'booking_id': str(booking.id),
            'space_name': booking.space.name,
            'check_in': booking.check_in.isoformat(),
            'check_out': booking.check_out.isoformat(),
            'workspace': booking.workspace.name,
        }
        
        # Generate QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(guest.qr_code_verification_code)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code image to BytesIO
        qr_image_bytes = BytesIO()
        img.save(qr_image_bytes, format='PNG')
        qr_image_bytes.seek(0)
        
        # Send notification with QR code
        from notifications.tasks import send_notification
        
        notification_data = {
            'qr_code_verification': guest.qr_code_verification_code,
            'check_in': str(booking.check_in),
            'check_out': str(booking.check_out),
            'space_name': booking.space.name,
            'booking_reference': str(booking.id),
        }
        
        send_notification.delay(
            user_id=None,  # Not a registered user
            notification_type='guest_qr_code',
            channel='email',
            recipient_email=guest.email,
            title=f'Your Check-in QR Code - {booking.space.name}',
            message=f'Hello {guest.first_name},\n\n'
                    f'Your QR code for checking in to {booking.space.name} is ready.\n'
                    f'Check-in opens: {booking.check_in}\n'
                    f'Check-out time: {booking.check_out}\n\n'
                    f'Please use the QR code attached or code: {guest.qr_code_verification_code}',
            data=notification_data
        )
        
        # Update guest QR code sent status
        guest.qr_code_sent = True
        guest.qr_code_sent_at = timezone.now()
        guest.save()
        
        logger.info(f"QR code email sent successfully to {guest.email}")
        return {
            'status': 'success',
            'message': f'QR code sent to {guest.email}',
            'guest_id': str(guest.id)
        }
    
    except Guest.DoesNotExist:
        logger.error(f"Guest {guest_id} not found")
        return {'status': 'error', 'message': 'Guest not found'}
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found")
        return {'status': 'error', 'message': 'Booking not found'}
    except Exception as exc:
        logger.error(f"Error sending guest QR code: {str(exc)}")
        # Retry after 5 minutes with exponential backoff
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


@shared_task
def send_guest_reminder_before_checkin(guest_id):
    """
    Send reminder email to guest before check-in
    Called 1 hour before check-in time
    """
    try:
        guest = Guest.objects.get(id=guest_id)
        booking = guest.booking
        
        logger.info(f"Sending check-in reminder to guest {guest.email}")
        
        from notifications.tasks import send_notification
        
        send_notification.delay(
            user_id=None,
            notification_type='guest_checkin_reminder',
            channel='email',
            recipient_email=guest.email,
            title=f'Reminder: Check-in Starting Soon - {booking.space.name}',
            message=f'Hello {guest.first_name},\n\n'
                    f'This is a reminder that check-in for {booking.space.name} starts in 1 hour.\n'
                    f'Check-in time: {booking.check_in}\n\n'
                    f'Please be ready with your QR code.',
            data={
                'verification_code': guest.qr_code_verification_code,
                'space_name': booking.space.name,
            }
        )
        
        logger.info(f"Reminder sent to {guest.email}")
        return {'status': 'success', 'message': 'Reminder sent'}
    
    except Guest.DoesNotExist:
        logger.error(f"Guest {guest_id} not found")
        return {'status': 'error', 'message': 'Guest not found'}
    except Exception as exc:
        logger.error(f"Error sending guest reminder: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_guest_receipt_after_checkout(guest_id):
    """
    Send receipt/confirmation email to guest after check-out
    """
    try:
        guest = Guest.objects.get(id=guest_id)
        booking = guest.booking
        
        logger.info(f"Sending check-out receipt to guest {guest.email}")
        
        from notifications.tasks import send_notification
        
        send_notification.delay(
            user_id=None,
            notification_type='guest_checkout_receipt',
            channel='email',
            recipient_email=guest.email,
            title=f'Check-out Confirmation - {booking.space.name}',
            message=f'Hello {guest.first_name},\n\n'
                    f'Thank you for staying at {booking.space.name}!\n'
                    f'Your check-out was completed at {guest.checked_out_at}.\n\n'
                    f'Booking Reference: {booking.id}\n'
                    f'Space: {booking.space.name}\n'
                    f'Check-in: {booking.check_in}\n'
                    f'Check-out: {booking.check_out}\n\n'
                    f'We hope to see you again!',
            data={
                'booking_id': str(booking.id),
                'space_name': booking.space.name,
            }
        )
        
        logger.info(f"Receipt sent to {guest.email}")
        return {'status': 'success', 'message': 'Receipt sent'}
    
    except Guest.DoesNotExist:
        logger.error(f"Guest {guest_id} not found")
        return {'status': 'error', 'message': 'Guest not found'}
    except Exception as exc:
        logger.error(f"Error sending guest receipt: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}
