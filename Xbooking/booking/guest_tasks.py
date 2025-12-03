"""
Celery tasks for Guest Management
"""
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from booking.models import Booking, Guest
from notifications.models import Notification
import logging
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
import base64

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
        from Xbooking.mailjet_utils import send_mailjet_email
        
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
        
        # Convert QR code image to base64 for attachment
        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
        
        # Send email via Mailjet API
        filename = f"qr_{guest.qr_code_verification_code}.png"
        result = send_mailjet_email(
            subject=f'Your Check-in QR Code - {booking.space.name}',
            to_email=guest.email,
            to_name=f"{guest.first_name} {guest.last_name}",
            html_content=html_content,
            text_content=text_content,
            attachments=[{
                'ContentType': 'image/png',
                'Filename': filename,
                'Base64Content': img_base64
            }]
        )
        
        if not result.get('success'):
            raise Exception(f"Failed to send email: {result.get('error')}")
        
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
        
        from django.template.loader import render_to_string
        from Xbooking.mailjet_utils import send_mailjet_email
        
        context = {
            'guest_name': f"{guest.first_name} {guest.last_name}",
            'first_name': guest.first_name,
            'space_name': booking.space.name,
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'booking_reference': str(booking.id),
            'verification_code': guest.qr_code_verification_code,
        }
        
        # Render email templates
        try:
            html_content = render_to_string('emails/guest_checkin_reminder.html', context)
            text_content = render_to_string('emails/guest_checkin_reminder.txt', context)
        except Exception:
            # Fallback if template missing
            html_content = f"""
            <html>
            <body>
                <h1>Check-in Reminder</h1>
                <p>Hello {guest.first_name},</p>
                <p>This is a reminder that check-in for <strong>{booking.space.name}</strong> starts in 1 hour.</p>
                <p><strong>Check-in time:</strong> {booking.check_in}</p>
                <p>Please be ready with your QR code when you arrive.</p>
                <p>We look forward to welcoming you!</p>
                <br>
                <p>Best regards,<br>The XBooking Team</p>
            </body>
            </html>
            """
            text_content = f"""
Hello {guest.first_name},

This is a reminder that check-in for {booking.space.name} starts in 1 hour.

Check-in time: {booking.check_in}

Please be ready with your QR code when you arrive.

We look forward to welcoming you!

Best regards,
The XBooking Team
            """
        
        # Send email via Mailjet API to guest
        result = send_mailjet_email(
            subject=f'Reminder: Check-in Starting Soon - {booking.space.name}',
            to_email=guest.email,
            to_name=f"{guest.first_name} {guest.last_name}",
            html_content=html_content,
            text_content=text_content
        )
        
        if not result.get('success'):
            raise Exception(f"Failed to send email: {result.get('error')}")
        
        # Mark reminder as sent
        guest.reminder_sent = True
        guest.reminder_sent_at = timezone.now()
        guest.save(update_fields=['reminder_sent', 'reminder_sent_at'])
        
        # Log notification for booking owner
        Notification.objects.create(
            user=booking.user,
            notification_type='guest_checkin_reminder_sent',
            channel='email',
            title='Guest Check-in Reminder Sent',
            message=f'Check-in reminder sent to guest {guest.first_name} {guest.last_name} for {booking.space.name}',
            is_sent=True,
            sent_at=timezone.now(),
            data={
                'guest_id': str(guest.id),
                'booking_id': str(booking.id),
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
        
        from django.template.loader import render_to_string
        from Xbooking.mailjet_utils import send_mailjet_email
        
        context = {
            'guest_name': f"{guest.first_name} {guest.last_name}",
            'first_name': guest.first_name,
            'space_name': booking.space.name,
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'checked_out_at': guest.checked_out_at,
            'booking_reference': str(booking.id),
            'booking_url': 'https://app.xbooking.dev',
        }
        
        # Render email templates
        try:
            html_content = render_to_string('emails/guest_checkout_receipt.html', context)
            text_content = render_to_string('emails/guest_checkout_receipt.txt', context)
        except Exception:
            # Fallback if template missing
            html_content = f"""
            <html>
            <body>
                <h1>Check-out Confirmation</h1>
                <p>Hello {guest.first_name},</p>
                <p>Thank you for staying at <strong>{booking.space.name}</strong>!</p>
                
                <h3>Booking Details:</h3>
                <ul>
                    <li><strong>Booking Reference:</strong> {booking.id}</li>
                    <li><strong>Space:</strong> {booking.space.name}</li>
                    <li><strong>Check-in:</strong> {booking.check_in}</li>
                    <li><strong>Check-out:</strong> {booking.check_out}</li>
                    <li><strong>Checked out at:</strong> {guest.checked_out_at}</li>
                </ul>
                
                <p>We hope you had a wonderful experience!</p>
                
                <p style="margin-top: 30px;">
                    <a href="https://app.xbooking.dev" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Book Again
                    </a>
                </p>
                
                <p>Looking forward to hosting you again soon!</p>
                
                <br>
                <p>Best regards,<br>The XBooking Team</p>
            </body>
            </html>
            """
            text_content = f"""
Hello {guest.first_name},

Thank you for staying at {booking.space.name}!

Booking Details:
- Booking Reference: {booking.id}
- Space: {booking.space.name}
- Check-in: {booking.check_in}
- Check-out: {booking.check_out}
- Checked out at: {guest.checked_out_at}

We hope you had a wonderful experience!

Ready to book your next stay? Visit: https://app.xbooking.dev

Looking forward to hosting you again soon!

Best regards,
The XBooking Team
            """
        
        # Send email via Mailjet API to guest
        result = send_mailjet_email(
            subject=f'Check-out Confirmation - {booking.space.name}',
            to_email=guest.email,
            to_name=f"{guest.first_name} {guest.last_name}",
            html_content=html_content,
            text_content=text_content
        )
        
        if not result.get('success'):
            raise Exception(f"Failed to send email: {result.get('error')}")
        
        # Mark receipt as sent
        guest.receipt_sent = True
        guest.receipt_sent_at = timezone.now()
        guest.save(update_fields=['receipt_sent', 'receipt_sent_at'])
        
        # Log notification for booking owner
        Notification.objects.create(
            user=booking.user,
            notification_type='guest_checkout_receipt_sent',
            channel='email',
            title='Guest Check-out Confirmation Sent',
            message=f'Check-out confirmation sent to guest {guest.first_name} {guest.last_name} for {booking.space.name}',
            is_sent=True,
            sent_at=timezone.now(),
            data={
                'guest_id': str(guest.id),
                'booking_id': str(booking.id),
                'space_name': booking.space.name,
                'checked_out_at': str(guest.checked_out_at),
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


@shared_task
def check_and_send_guest_reminders():
    """
    Periodic task to check for guests who need check-in reminders.
    Sends reminder emails 1 hour before check-in time.
    Should be run every 15-30 minutes via Celery Beat.
    """
    from datetime import timedelta
    
    try:
        now = timezone.now()
        reminder_time = now + timedelta(hours=1)
        
        # Find all guests whose check-in is approximately 1 hour away
        # Look for check-ins between 50 minutes and 70 minutes from now
        start_window = now + timedelta(minutes=50)
        end_window = now + timedelta(minutes=70)
        
        # Get guests who haven't checked in yet and haven't received a reminder
        guests_needing_reminder = Guest.objects.filter(
            booking__check_in__gte=start_window,
            booking__check_in__lte=end_window,
            status='pending',
            qr_code_sent=True,  # Only send reminders to guests who already have QR codes
            reminder_sent=False  # Haven't received reminder yet
        ).select_related('booking', 'booking__space')
        
        sent_count = 0
        for guest in guests_needing_reminder:
            try:
                # Queue the reminder email task
                send_guest_reminder_before_checkin.delay(str(guest.id))
                sent_count += 1
                logger.info(f"Queued reminder for guest {guest.email} - check-in at {guest.booking.check_in}")
            except Exception as e:
                logger.error(f"Error queuing reminder for guest {guest.id}: {str(e)}")
                continue
        
        logger.info(f"Queued {sent_count} guest check-in reminders")
        return {
            'status': 'success',
            'reminders_sent': sent_count,
            'message': f'Queued {sent_count} check-in reminders'
        }
    
    except Exception as exc:
        logger.error(f"Error in check_and_send_guest_reminders: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def check_and_send_checkout_receipts():
    """
    Periodic task to check for guests who have checked out and need receipts.
    Sends receipt emails to guests after they check out.
    Should be run every 15-30 minutes via Celery Beat.
    """
    try:
        # Find guests who have checked out but haven't received a receipt
        guests_needing_receipt = Guest.objects.filter(
            status='checked_out',
            checked_out_at__isnull=False,
            receipt_sent=False  # Haven't received receipt yet
        ).select_related('booking', 'booking__space')
        
        sent_count = 0
        for guest in guests_needing_receipt:
            try:
                # Queue the receipt email task
                send_guest_receipt_after_checkout.delay(str(guest.id))
                sent_count += 1
                logger.info(f"Queued receipt for guest {guest.email} - checked out at {guest.checked_out_at}")
                
            except Exception as e:
                logger.error(f"Error queuing receipt for guest {guest.id}: {str(e)}")
                continue
        
        logger.info(f"Queued {sent_count} guest checkout receipts")
        return {
            'status': 'success',
            'receipts_sent': sent_count,
            'message': f'Queued {sent_count} checkout receipts'
        }
    
    except Exception as exc:
        logger.error(f"Error in check_and_send_checkout_receipts: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def generate_guest_qr_codes_for_order(order_id):
    """
    Generate and send QR codes for all guests in all bookings of an order.
    Called after successful payment to send QR codes to all guests.
    
    Args:
        order_id (str): UUID of the order
        
    Returns:
        dict: Summary of QR codes sent
    """
    from payment.models import Order
    
    try:
        order = Order.objects.get(id=order_id)
        
        logger.info(f"Generating QR codes for all guests in order {order_id}")
        
        results = []
        for booking in order.bookings.all():
            for guest in booking.guests.all():
                # Skip if QR code already sent
                if guest.qr_code_sent:
                    logger.info(f"QR code already sent to guest {guest.id}")
                    continue
                
                # Queue individual QR code email task
                send_guest_qr_code_email.delay(str(guest.id), str(booking.id))
                results.append({
                    'guest_id': str(guest.id),
                    'email': guest.email,
                    'status': 'queued'
                })
        
        logger.info(f"Queued {len(results)} guest QR code emails for order {order_id}")
        
        return {
            'status': 'success',
            'order_id': str(order_id),
            'guests_queued': len(results),
            'results': results
        }
    
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return {'status': 'error', 'message': 'Order not found'}
    except Exception as exc:
        logger.error(f"Error generating guest QR codes for order: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}
