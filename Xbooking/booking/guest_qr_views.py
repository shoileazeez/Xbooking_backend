"""
Guest QR Code Generation Views
Separate endpoint for generating QR codes for guests after payment
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from drf_spectacular.utils import extend_schema
import secrets
import string

from booking.models import Booking, Guest
from booking.guest_serializers import GuestSerializer
from payment.models import Order
from notifications.models import Notification


class GenerateGuestQRCodesView(APIView):
    """Generate QR codes for all guests in a booking (after payment)"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Generate QR codes for booking guests",
        description="Generate and send QR codes to all guests. Requires payment to be completed.",
        tags=["Guest QR Codes"],
        responses={
            200: {"type": "object", "properties": {"message": {"type": "string"}, "guests": {"type": "array"}}},
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
            403: {"type": "object", "properties": {"error": {"type": "string"}}},
            404: {"type": "object", "properties": {"error": {"type": "string"}}}
        }
    )
    @transaction.atomic
    def post(self, request, booking_id):
        """Generate QR codes for all guests in booking"""
        try:
            booking = Booking.objects.select_related('user').get(id=booking_id)
            
            # Check if user owns the booking
            if booking.user != request.user:
                return Response(
                    {'error': 'You do not have permission to generate QR codes for this booking'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if booking has an order
        try:
            order = Order.objects.get(bookings=booking)
        except Order.DoesNotExist:
            return Response(
                {'error': 'No order found for this booking. Please create an order first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check payment status
        if order.status not in ['paid', 'processing', 'completed']:
            return Response(
                {
                    'error': f'Payment required. Order status is "{order.status}". QR codes can only be generated for paid, processing, or completed orders.',
                    'order_status': order.status,
                    'order_number': order.order_number
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all guests for this booking
        guests = booking.guests.all()
        
        if not guests.exists():
            return Response(
                {'error': 'No guests found for this booking. Please add guests first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate QR codes for guests that don't have one
        updated_guests = []
        for guest in guests:
            if not guest.qr_code_verification_code:
                # Generate unique verification code
                guest.qr_code_verification_code = self._generate_verification_code()
                guest.qr_code_sent = True
                guest.qr_code_sent_at = timezone.now()
                guest.save()
                
                # Send QR code email
                from booking.guest_tasks import send_guest_qr_code_email
                send_guest_qr_code_email.delay(str(guest.id), str(booking.id))
                
                # Create in-app notification
                Notification.objects.create(
                    user=booking.user,
                    notification_type='guest_qr_generated',
                    channel='in_app',
                    title='Guest QR Code Generated',
                    message=f'QR code generated for guest {guest.first_name} {guest.last_name}',
                    is_sent=True,
                    sent_at=timezone.now(),
                    data={
                        'guest_id': str(guest.id),
                        'booking_id': str(booking.id),
                        'guest_email': guest.email
                    }
                )
                
                updated_guests.append(guest)
        
        if not updated_guests:
            return Response(
                {
                    'message': 'All guests already have QR codes',
                    'guests': GuestSerializer(guests, many=True).data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {
                'message': f'Successfully generated QR codes for {len(updated_guests)} guest(s). Emails sent.',
                'guests': GuestSerializer(guests, many=True).data,
                'order_status': order.status
            },
            status=status.HTTP_200_OK
        )
    
    def _generate_verification_code(self, length=12):
        """Generate random verification code"""
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))


class ResendGuestQRCodeView(APIView):
    """Resend QR code for a specific guest"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Resend QR code for a guest",
        description="Resend QR code email to a specific guest",
        tags=["Guest QR Codes"],
        responses={
            200: GuestSerializer,
            403: {"type": "object", "properties": {"error": {"type": "string"}}},
            404: {"type": "object", "properties": {"error": {"type": "string"}}}
        }
    )
    def post(self, request, guest_id):
        """Resend QR code to guest"""
        try:
            guest = Guest.objects.select_related('booking__user').get(id=guest_id)
            
            # Check if user owns the booking
            if guest.booking.user != request.user:
                return Response(
                    {'error': 'You do not have permission to resend QR code for this guest'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Guest not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if guest has QR code
        if not guest.qr_code_verification_code:
            return Response(
                {'error': 'Guest does not have a QR code yet. Please generate QR codes for the booking first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Resend QR code email
        from booking.guest_tasks import send_guest_qr_code_email
        send_guest_qr_code_email.delay(str(guest.id), str(guest.booking.id))
        
        # Update sent timestamp
        guest.qr_code_sent_at = timezone.now()
        guest.save()
        
        # Create notification
        Notification.objects.create(
            user=guest.booking.user,
            notification_type='guest_qr_resent',
            channel='in_app',
            title='Guest QR Code Resent',
            message=f'QR code resent to {guest.first_name} {guest.last_name} ({guest.email})',
            is_sent=True,
            sent_at=timezone.now(),
            data={
                'guest_id': str(guest.id),
                'booking_id': str(guest.booking.id),
                'guest_email': guest.email
            }
        )
        
        return Response(
            {
                'message': f'QR code resent to {guest.email}',
                'guest': GuestSerializer(guest).data
            },
            status=status.HTTP_200_OK
        )
