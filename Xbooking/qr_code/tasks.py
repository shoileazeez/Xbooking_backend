"""
Celery tasks for QR code generation and notifications
"""
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from notifications.models import Notification, NotificationPreference
from payment.models import Order
import qrcode
import io
import uuid
from datetime import timedelta


@shared_task
def generate_qr_code_for_order(order_id):
    """
    Generate QR code for an order and save it
    """
    try:
        from qr_code.models import OrderQRCode
        order = Order.objects.get(id=order_id)
        
        # Generate unique verification code
        verification_code = f"ORD-{uuid.uuid4().hex[:12].upper()}"
        
        # QR code data - includes order number, verification code, and check-in URL
        qr_data = f"https://xbooking.com/verify/{verification_code}?order={order.order_number}"
        
        # Generate QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Convert to image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to file
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        # Determine expiry based on the latest checkout time from order bookings
        latest_checkout = None
        for booking in order.bookings.all():
            if booking.check_out:
                if latest_checkout is None or booking.check_out > latest_checkout:
                    latest_checkout = booking.check_out
        
        # Fallback to 24 hours if no checkout time found
        expires_at = latest_checkout if latest_checkout else (timezone.now() + timedelta(hours=24))
        
        # Create or update QR code record
        qr_code, created = OrderQRCode.objects.update_or_create(
            order=order,
            defaults={
                'verification_code': verification_code,
                'qr_code_data': qr_data,
                'status': 'generated',
                'expires_at': expires_at,
            }
        )
        
        # Save image
        filename = f"qr_{order.order_number}_{verification_code}.png"
        qr_code.qr_code_image.save(filename, ContentFile(img_io.getvalue()))
        qr_code.save()
        
        # Send QR code to user via email
        send_qr_code_email.delay(order_id, qr_code.id)
        
        return {
            'success': True,
            'qr_code_id': str(qr_code.id),
            'verification_code': verification_code,
            'message': 'QR code generated successfully'
        }
    except Order.DoesNotExist:
        return {
            'success': False,
            'error': f'Order {order_id} not found'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_qr_code_email(order_id, qr_code_id):
    """
    Send QR code to user via email
    """
    try:
        from qr_code.models import OrderQRCode
        order = Order.objects.get(id=order_id)
        qr_code = OrderQRCode.objects.get(id=qr_code_id)
        
        # Check user notification preference
        if hasattr(order.user, 'notification_preferences'):
            if not order.user.notification_preferences.email_qr_code:
                return {'success': True, 'message': 'User disabled email notifications'}
        
        # Prepare email content
        context = {
            'order_number': order.order_number,
            'user_name': order.user.full_name or order.user.email,
            'total_amount': order.total_amount,
            'bookings_count': order.bookings.count(),
        }
        
        # Render HTML template
        html_content = render_to_string('emails/qr_code_email.html', context)
        text_content = render_to_string('emails/qr_code_email.txt', context)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=f'Your QR Code for Order {order.order_number}',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Attach QR code image
        if qr_code.qr_code_image:
            email.attach_file(qr_code.qr_code_image.path)
        
        # Send email
        email.send()
        
        # Update QR code status
        qr_code.status = 'sent'
        qr_code.sent_at = timezone.now()
        qr_code.save()
        
        # Log notification
        Notification.objects.create(
            user=order.user,
            notification_type='qr_code_generated',
            channel='email',
            title='QR Code Generated',
            message=f'QR code for order {order.order_number} has been sent to your email',
            is_sent=True,
            sent_at=timezone.now(),
            data={
                'order_id': str(order.id),
                'qr_code_id': str(qr_code.id),
                'verification_code': qr_code.verification_code
            }
        )
        
        return {
            'success': True,
            'message': 'QR code email sent successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_order_confirmation_email(order_id):
    """
    Send order confirmation email
    """
    try:
        order = Order.objects.get(id=order_id)
        
        # Check user notification preference
        if hasattr(order.user, 'notification_preferences'):
            if not order.user.notification_preferences.email_order_confirmation:
                return {'success': True, 'message': 'User disabled email notifications'}
        
        # Prepare email content
        context = {
            'order_number': order.order_number,
            'user_name': order.user.full_name or order.user.email,
            'total_amount': order.total_amount,
            'bookings': order.bookings.all(),
        }
        
        # Render HTML template
        html_content = render_to_string('emails/order_confirmation_email.html', context)
        text_content = render_to_string('emails/order_confirmation_email.txt', context)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=f'Order Confirmation: {order.order_number}',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        
        # Log notification
        Notification.objects.create(
            user=order.user,
            notification_type='order_created',
            channel='email',
            title='Order Created',
            message=f'Your order {order.order_number} has been created',
            is_sent=True,
            sent_at=timezone.now(),
            data={'order_id': str(order.id)}
        )
        
        return {
            'success': True,
            'message': 'Order confirmation email sent successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_payment_confirmation_email(order_id):
    """
    Send payment confirmation email
    """
    try:
        order = Order.objects.get(id=order_id)
        payment = order.payment
        
        # Check user notification preference
        if hasattr(order.user, 'notification_preferences'):
            if not order.user.notification_preferences.email_payment_confirmation:
                return {'success': True, 'message': 'User disabled email notifications'}
        
        # Prepare email content
        context = {
            'order_number': order.order_number,
            'user_name': order.user.full_name or order.user.email,
            'total_amount': order.total_amount,
            'payment_method': payment.payment_method.upper() if payment else 'Unknown',
            'transaction_id': payment.gateway_transaction_id if payment else 'N/A',
            'bookings': order.bookings.all(),
        }
        
        # Render HTML template
        html_content = render_to_string('emails/payment_confirmation_email.html', context)
        text_content = render_to_string('emails/payment_confirmation_email.txt', context)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=f'Payment Confirmed: {order.order_number}',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        
        # Log notification
        Notification.objects.create(
            user=order.user,
            notification_type='payment_successful',
            channel='email',
            title='Payment Successful',
            message=f'Payment for order {order.order_number} confirmed',
            is_sent=True,
            sent_at=timezone.now(),
            data={'order_id': str(order.id), 'payment_id': str(payment.id) if payment else None}
        )
        
        return {
            'success': True,
            'message': 'Payment confirmation email sent successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_booking_reminder(booking_id):
    """
    Send booking reminder email before check-in
    """
    try:
        from booking.models import Booking
        
        booking = Booking.objects.get(id=booking_id)
        user = booking.user
        
        # Check user notification preference
        if hasattr(user, 'notification_preferences'):
            if not user.notification_preferences.email_booking_reminder:
                return {'success': True, 'message': 'User disabled email notifications'}
        
        # Prepare email content
        context = {
            'user_name': user.full_name or user.email,
            'space_name': booking.space.name,
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'location': booking.space.branch.name if hasattr(booking.space, 'branch') else 'N/A',
        }
        
        # Render HTML template
        html_content = render_to_string('emails/booking_reminder_email.html', context)
        text_content = render_to_string('emails/booking_reminder_email.txt', context)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=f'Reminder: Your booking at {booking.space.name}',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        
        return {
            'success': True,
            'message': 'Booking reminder email sent successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_upcoming_booking_reminders():
    """
    Find all confirmed bookings starting in the next hour and send reminders.
    This is called by Celery Beat every hour.
    """
    try:
        from booking.models import Booking
        
        now = timezone.now()
        one_hour_later = now + timedelta(hours=1)
        
        # Find confirmed bookings that start in the next hour
        upcoming_bookings = Booking.objects.filter(
            status='confirmed',
            check_in__gte=now,
            check_in__lte=one_hour_later
        )
        
        sent_count = 0
        for booking in upcoming_bookings:
            # Queue individual reminder
            send_booking_reminder.delay(str(booking.id))
            sent_count += 1
        
        return {
            'success': True,
            'reminders_queued': sent_count,
            'message': f'Queued {sent_count} booking reminders'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_booking_qr_codes_for_order(order_id):
    """
    Generate QR code for each booking in an order (for the booker).
    Each booking gets its own QR code stored in BookingQRCode model.
    After generating all QR codes, sends an email to the booker with all QR codes attached.
    
    Args:
        order_id (str): UUID of the order
        
    Returns:
        dict: Result with QR code IDs
    """
    try:
        from qr_code.models import BookingQRCode
        from booking.models import Booking
        
        order = Order.objects.get(id=order_id)
        booking_qr_codes = []
        
        for booking in order.bookings.filter(status='confirmed'):
            # Skip if QR code already exists for this booking
            if hasattr(booking, 'qr_code') and booking.qr_code:
                booking_qr_codes.append(booking.qr_code)
                continue
            
            # Generate unique verification code
            verification_code = f"BKG-{uuid.uuid4().hex[:12].upper()}"
            
            # QR code data - includes booking ID, space info, verification code
            qr_data = {
                'type': 'booking',
                'verification_code': verification_code,
                'booking_id': str(booking.id),
                'space_id': str(booking.space.id),
                'space_name': booking.space.name,
                'check_in': booking.check_in.isoformat() if booking.check_in else None,
                'check_out': booking.check_out.isoformat() if booking.check_out else None,
            }
            qr_url = f"https://xbooking.com/verify-booking/{verification_code}?booking={booking.id}"
            
            # Generate QR code image
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            # Convert to image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to file
            img_io = io.BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)
            
            # Set expiry to booking checkout time
            expires_at = booking.check_out if booking.check_out else (timezone.now() + timedelta(hours=24))
            
            # Create BookingQRCode record
            booking_qr = BookingQRCode.objects.create(
                booking=booking,
                order=order,
                verification_code=verification_code,
                qr_code_data=str(qr_data),
                status='generated',
                expires_at=expires_at,
            )
            
            # Save image
            filename = f"booking_qr_{booking.id}_{verification_code}.png"
            booking_qr.qr_code_image.save(filename, ContentFile(img_io.getvalue()))
            booking_qr.save()
            
            booking_qr_codes.append(booking_qr)
        
        # Send email with all booking QR codes
        if booking_qr_codes:
            send_booking_qr_codes_email.delay(order_id)
        
        return {
            'success': True,
            'qr_codes_generated': len(booking_qr_codes),
            'qr_code_ids': [str(qr.id) for qr in booking_qr_codes],
            'message': f'Generated {len(booking_qr_codes)} booking QR codes'
        }
    
    except Order.DoesNotExist:
        return {
            'success': False,
            'error': f'Order {order_id} not found'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_booking_qr_codes_email(order_id):
    """
    Send email to booker with QR codes for all their bookings.
    Supports both single and multiple bookings in one email.
    
    Args:
        order_id (str): UUID of the order
        
    Returns:
        dict: Result status
    """
    try:
        from qr_code.models import BookingQRCode
        
        order = Order.objects.get(id=order_id)
        user = order.user
        
        # Check user notification preference
        if hasattr(user, 'notification_preferences'):
            if not user.notification_preferences.email_qr_code:
                return {'success': True, 'message': 'User disabled QR code email notifications'}
        
        # Get all booking QR codes for this order
        booking_qr_codes = BookingQRCode.objects.filter(order=order).select_related('booking', 'booking__space')
        
        if not booking_qr_codes.exists():
            return {'success': False, 'error': 'No booking QR codes found for order'}
        
        # Prepare email content
        bookings_data = []
        for qr in booking_qr_codes:
            bookings_data.append({
                'space_name': qr.booking.space.name,
                'check_in': qr.booking.check_in,
                'check_out': qr.booking.check_out,
                'verification_code': qr.verification_code,
            })
        
        context = {
            'order_number': order.order_number,
            'user_name': user.full_name or user.email,
            'bookings_count': booking_qr_codes.count(),
            'bookings': bookings_data,
            'is_multiple': booking_qr_codes.count() > 1,
        }
        
        # Try to render template, fallback to basic HTML
        try:
            html_content = render_to_string('emails/booking_qr_codes_email.html', context)
            text_content = render_to_string('emails/booking_qr_codes_email.txt', context)
        except Exception:
            # Fallback if template doesn't exist
            bookings_html = ""
            bookings_text = ""
            for b in bookings_data:
                bookings_html += f"<li><strong>{b['space_name']}</strong> - Check-in: {b['check_in']}, Check-out: {b['check_out']}</li>"
                bookings_text += f"- {b['space_name']} - Check-in: {b['check_in']}, Check-out: {b['check_out']}\n"
            
            html_content = f"""
            <html>
            <body>
            <h1>Your Booking QR Codes</h1>
            <p>Hello {context['user_name']},</p>
            <p>Your payment for order <strong>{context['order_number']}</strong> has been confirmed!</p>
            <p>Please find attached your QR code(s) for check-in at the following booking(s):</p>
            <ul>{bookings_html}</ul>
            <p>Present the appropriate QR code when you arrive at each space for quick check-in.</p>
            <p>Thank you for choosing XBooking!</p>
            </body>
            </html>
            """
            text_content = f"""
Your Booking QR Codes

Hello {context['user_name']},

Your payment for order {context['order_number']} has been confirmed!

Please find attached your QR code(s) for check-in at the following booking(s):
{bookings_text}

Present the appropriate QR code when you arrive at each space for quick check-in.

Thank you for choosing XBooking!
            """
        
        # Create email
        subject = f'Your Booking QR Code{"s" if booking_qr_codes.count() > 1 else ""} - Order {order.order_number}'
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Attach all QR code images
        for qr in booking_qr_codes:
            if qr.qr_code_image:
                try:
                    filename = f"QR_{qr.booking.space.name.replace(' ', '_')}_{qr.verification_code}.png"
                    email.attach_file(qr.qr_code_image.path)
                except Exception as e:
                    # If file not accessible, try reading from storage
                    pass
        
        # Send email
        email.send()
        
        # Update QR code statuses
        booking_qr_codes.update(status='sent', sent_at=timezone.now())
        
        # Log notification
        Notification.objects.create(
            user=user,
            notification_type='booking_qr_codes_sent',
            channel='email',
            title='Booking QR Codes Sent',
            message=f'Your QR code(s) for order {order.order_number} have been sent to your email',
            is_sent=True,
            sent_at=timezone.now(),
            data={
                'order_id': str(order.id),
                'bookings_count': booking_qr_codes.count()
            }
        )
        
        return {
            'success': True,
            'message': f'Booking QR codes email sent successfully with {booking_qr_codes.count()} QR code(s)'
        }
    
    except Order.DoesNotExist:
        return {
            'success': False,
            'error': f'Order {order_id} not found'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def expire_booking_qr_codes():
    """
    Mark BookingQRCode records as expired based on booking status:
    - Booking is completed (checked in AND checked out)
    - OR checkout date/time has passed
    """
    try:
        from qr_code.models import BookingQRCode
        
        now = timezone.now()
        expired_count = 0
        
        # Get all active booking QR codes
        active_qr_codes = BookingQRCode.objects.filter(
            status__in=['generated', 'sent']
        ).select_related('booking')
        
        for qr_code in active_qr_codes:
            booking = qr_code.booking
            should_expire = False
            
            # Expire if booking is completed
            if booking.status == 'completed':
                should_expire = True
            
            # Expire if checkout date/time has passed
            elif booking.check_out and booking.check_out < now:
                should_expire = True
            
            if should_expire:
                qr_code.status = 'expired'
                qr_code.save()
                expired_count += 1
        
        return {
            'success': True,
            'expired_count': expired_count,
            'message': f'{expired_count} booking QR codes marked as expired'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
