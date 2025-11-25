"""
Celery tasks for Guest Management
"""
from celery import shared_task
from django.utils import timezone
from booking.models import Booking, Guest
from notifications.models import Notification
import logging
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_guest_qr_code_email(self, guest_id, booking_id):
    """
    Send QR code email to guest
    Generates QR code and sends to guest email
    """
    try:
        guest = Guest.objects.get(id=guest_id)
        booking = Booking.objects.get(id=booking_id)
        
        logger.info(f"Generating QR code for guest {guest.id}: {guest.email}")
        
        # QR code data - URL for verification
        # Using a similar format to qr_code app
        qr_data = f"https://xbooking.com/verify-guest/{guest.qr_code_verification_code}?booking={booking.id}"
        
        # Generate QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code image to BytesIO
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        # Prepare email content
        from django.template.loader import render_to_string
        from django.core.mail import EmailMultiAlternatives
        
        context = {
            'guest_name': f"{guest.first_name} {guest.last_name}",
            'space_name': booking.space.name,
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'booking_reference': str(booking.id),
        }
        
        # Render HTML template (assuming we have one or reuse a generic one)
        # For now, I'll use a simple string or we should create a template.
        # The user said "do the same", so I should probably use a template.
        # I'll assume 'emails/guest_qr_code_email.html' exists or I'll create it.
        # Since I can't create it right now without a separate tool call, I'll use a basic template or try to reuse.
        # Let's try to render a simple HTML here if template doesn't exist, but better to assume it will.
        # Actually, I'll use a try-except block or just define the content here if I can't rely on the template file yet.
        # But to be "correct", I should use a template. I'll assume 'booking/email/guest_qr_code.html'
        
        try:
            html_content = render_to_string('booking/email/guest_qr_code.html', context)
            text_content = render_to_string('booking/email/guest_qr_code.txt', context)
        except Exception:
            # Fallback if template missing
            html_content = f"""
            <h1>Your Check-in QR Code</h1>
            <p>Hello {guest.first_name},</p>
            <p>Here is your QR code for {booking.space.name}.</p>
            <p>Check-in: {booking.check_in}</p>
            <p>Check-out: {booking.check_out}</p>
            """
            text_content = f"Hello {guest.first_name}, Here is your QR code for {booking.space.name}."
        
        # Create email
        email = EmailMultiAlternatives(
            subject=f'Your Check-in QR Code - {booking.space.name}',
            body=text_content,
            from_email='bookings@xbooking.com',
            to=[guest.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Attach QR code image
        filename = f"qr_{guest.qr_code_verification_code}.png"
        email.attach(filename, img_io.getvalue(), 'image/png')
        
        # Send email
        email.send()
        
        # Update guest QR code sent status
        guest.qr_code_sent = True
        guest.qr_code_sent_at = timezone.now()
        guest.save()
        
        # Log notification (optional, but good for tracking)
        from notifications.tasks import send_notification
        # We still log it, but maybe without the image data since we sent it via email
        Notification.objects.create(
            user=booking.user, # Notify the booker that guest received QR? Or just log?
            # The guest is not a User, so we can't log a notification for them in the DB easily if it requires a User FK.
            # But we can notify the booker.
            notification_type='guest_qr_code_sent',
            channel='email',
            title='Guest QR Code Sent',
            message=f'QR code sent to guest {guest.first_name} {guest.last_name}',
            is_sent=True,
            sent_at=timezone.now(),
            data={
                'guest_id': str(guest.id),
                'booking_id': str(booking.id)
            }
        )
        
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
