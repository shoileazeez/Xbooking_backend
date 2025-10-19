"""
Celery tasks for QR code generation and notifications
"""
from celery import shared_task
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
        
        # Create or update QR code record
        qr_code, created = OrderQRCode.objects.update_or_create(
            order=order,
            defaults={
                'verification_code': verification_code,
                'qr_code_data': qr_data,
                'status': 'generated',
                'expires_at': timezone.now() + timedelta(hours=24),  # Valid for 24 hours
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
            'user_name': order.user.first_name or order.user.email,
            'total_amount': order.total_amount,
            'verification_code': qr_code.verification_code,
            'bookings_count': order.bookings.count(),
        }
        
        # Render HTML template
        html_content = render_to_string('emails/qr_code_email.html', context)
        text_content = render_to_string('emails/qr_code_email.txt', context)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=f'Your QR Code for Order {order.order_number}',
            body=text_content,
            from_email='bookings@xbooking.com',
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
            'user_name': order.user.first_name or order.user.email,
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
            from_email='bookings@xbooking.com',
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
            'user_name': order.user.first_name or order.user.email,
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
            from_email='bookings@xbooking.com',
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
def expire_old_qr_codes():
    """
    Mark old QR codes as expired (scheduled task)
    """
    try:
        from qr_code.models import OrderQRCode

        expired_qrs = OrderQRCode.objects.filter(
            expires_at__lt=timezone.now(),
            status__in=['generated', 'sent']
        )
        
        count = expired_qrs.update(status='expired')
        
        return {
            'success': True,
            'expired_count': count,
            'message': f'{count} QR codes marked as expired'
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
            'user_name': user.first_name or user.email,
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
            from_email='bookings@xbooking.com',
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
