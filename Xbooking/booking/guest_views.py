"""
Guest Management Views for Bookings
Allows guests to check-in/out using QR codes
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
import secrets
import string

from booking.models import Booking, Guest
from booking.guest_serializers import (
    GuestSerializer, AddGuestsSerializer,
    GuestCheckInSerializer, GuestCheckOutSerializer,
    BookingGuestListSerializer
)
from workspace.permissions import check_workspace_member
from drf_spectacular.utils import extend_schema


class AddGuestsToBookingView(APIView):
    """Add guests to a booking"""
    permission_classes = [IsAuthenticated]
    serializer_class = AddGuestsSerializer
    
    @extend_schema(
        summary="Add guests to booking",
        description="Add multiple guests to a booking and generate QR codes",
        tags=["Booking Guests"],
        request=AddGuestsSerializer,
        responses={
            201: {"type": "object", "properties": {"message": {"type": "string"}, "guests": {"type": "array"}}},
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    @transaction.atomic
    def post(self, request, booking_id):
        """Add guests to booking"""
        try:
            booking = Booking.objects.get(id=booking_id)
            
            # Check if user owns the booking
            if booking.user != request.user:
                return Response(
                    {'error': 'You do not have permission to add guests to this booking'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AddGuestsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        guests_data = serializer.validated_data['guests']
        
        # Validate number of guests doesn't exceed booking limit
        total_guests = booking.number_of_guests
        existing_guests_count = booking.guests.count()
        
        if existing_guests_count + len(guests_data) > total_guests:
            return Response(
                {
                    'error': f'Cannot add {len(guests_data)} guests. Booking allows {total_guests} guests total. '
                             f'Already has {existing_guests_count} guests.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_guests = []
        for guest_data in guests_data:
            guest = Guest.objects.create(
                booking=booking,
                first_name=guest_data['first_name'],
                last_name=guest_data['last_name'],
                email=guest_data['email'],
                phone=guest_data.get('phone', ''),
                status='pending'  # QR code will be generated after payment
            )
            
            created_guests.append(GuestSerializer(guest).data)
        
        return Response(
            {
                'message': f'Successfully added {len(created_guests)} guest(s). QR codes will be sent after payment is confirmed.',
                'guests': created_guests
            },
            status=status.HTTP_201_CREATED
        )
    
    def _generate_verification_code(self, length=12):
        """Generate random verification code"""
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))


class GetBookingGuestsView(APIView):
    """Get all guests for a booking"""
    permission_classes = [IsAuthenticated]
    serializer_class = GuestSerializer
    
    @extend_schema(
        summary="Get booking guests",
        description="Get all guests for a specific booking",
        tags=["Booking Guests"],
        responses={
            200: BookingGuestListSerializer,
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, booking_id):
        """Get booking guests"""
        try:
            booking = Booking.objects.get(id=booking_id)
            
            # Check if user owns the booking
            if booking.user != request.user:
                 # Allow workspace staff/admin to view guests too
                 # We need to import check_workspace_member here or check workspace admin
                 if not check_workspace_member(request.user, booking.workspace, ['staff', 'manager', 'admin']):
                    return Response(
                        {'error': 'You do not have permission to view this booking'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            guests = booking.guests.all().order_by('created_at')
            checked_in_count = guests.filter(status='checked_in').count()
            
            response_data = {
                'booking_id': str(booking.id),
                'total_guests': guests.count(),
                'checked_in_count': checked_in_count,
                'guests': GuestSerializer(guests, many=True).data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class GuestCheckInView(APIView):
    """Guest check-in using QR code verification code"""
    permission_classes = []  # Public endpoint for guests
    serializer_class = GuestCheckInSerializer
    
    @extend_schema(
        summary="Guest check-in",
        description="Check-in guest using QR code verification code",
        tags=["Guest Check-in/Out"],
        request=GuestCheckInSerializer,
        responses={
            200: GuestSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    @transaction.atomic
    def post(self, request):
        """Check-in guest"""
        serializer = GuestCheckInSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        verification_code = serializer.validated_data['verification_code']
        
        try:
            guest = Guest.objects.get(qr_code_verification_code=verification_code)
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if guest is already checked in
        if guest.status == 'checked_in':
            return Response(
                {'error': f'Guest {guest.first_name} is already checked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if guest is within check-in window
        booking = guest.booking
        now = timezone.now()
        if now < booking.check_in:
            return Response(
                {'error': f'Check-in window not open yet. Opens at {booking.check_in}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if now > booking.check_out:
            return Response(
                {'error': f'Check-in window closed. Closed at {booking.check_out}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check-in guest
        guest.status = 'checked_in'
        guest.checked_in_at = now
        guest.save()
        
        return Response(
            {
                **GuestSerializer(guest).data,
                'message': f'Welcome {guest.first_name}! You have been checked in successfully.'
            },
            status=status.HTTP_200_OK
        )


class GuestCheckOutView(APIView):
    """Guest check-out using QR code verification code"""
    permission_classes = []  # Public endpoint for guests
    serializer_class = GuestCheckOutSerializer
    
    @extend_schema(
        summary="Guest check-out",
        description="Check-out guest using QR code verification code",
        tags=["Guest Check-in/Out"],
        request=GuestCheckOutSerializer,
        responses={
            200: GuestSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    @transaction.atomic
    def post(self, request):
        """Check-out guest"""
        serializer = GuestCheckOutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        verification_code = serializer.validated_data['verification_code']
        
        try:
            guest = Guest.objects.get(qr_code_verification_code=verification_code)
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if guest is checked in
        if guest.status != 'checked_in':
            return Response(
                {'error': f'Guest {guest.first_name} is not checked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check-out guest
        guest.status = 'checked_out'
        guest.checked_out_at = timezone.now()
        guest.save()
        
        return Response(
            {
                **GuestSerializer(guest).data,
                'message': f'Thank you {guest.first_name}! You have been checked out successfully.'
            },
            status=status.HTTP_200_OK
        )


class AdminCheckInGuestView(APIView):
    """Admin endpoint to check-in guest manually"""
    permission_classes = [IsAuthenticated]
    serializer_class = GuestSerializer
    
    @extend_schema(
        summary="Admin manual guest check-in",
        description="Admin manually checks in guest",
        tags=["Admin Guest Management"],
        responses={
            200: GuestSerializer,
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    @transaction.atomic
    def post(self, request, guest_id):
        """Admin check-in guest"""
        try:
            guest = Guest.objects.select_related('booking__workspace').get(id=guest_id)
            workspace = guest.booking.workspace
            
            # Check if user is workspace admin/manager/staff
            if not check_workspace_member(request.user, workspace, ['staff', 'manager', 'admin']):
                return Response(
                    {'error': 'You do not have permission to perform this action'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Guest not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if guest.status == 'checked_in':
            return Response(
                {'error': 'Guest is already checked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guest.status = 'checked_in'
        guest.checked_in_at = timezone.now()
        guest.save()
        
        return Response(
            GuestSerializer(guest).data,
            status=status.HTTP_200_OK
        )


class AdminCheckOutGuestView(APIView):
    """Admin endpoint to check-out guest manually"""
    permission_classes = [IsAuthenticated]
    serializer_class = GuestSerializer
    
    @extend_schema(
        summary="Admin manual guest check-out",
        description="Admin manually checks out guest",
        tags=["Admin Guest Management"],
        responses={
            200: GuestSerializer,
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    @transaction.atomic
    def post(self, request, guest_id):
        """Admin check-out guest"""
        try:
            guest = Guest.objects.select_related('booking__workspace').get(id=guest_id)
            workspace = guest.booking.workspace
            
            # Check if user is workspace admin/manager/staff
            if not check_workspace_member(request.user, workspace, ['staff', 'manager', 'admin']):
                return Response(
                    {'error': 'You do not have permission to perform this action'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Guest not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if guest.status != 'checked_in':
            return Response(
                {'error': 'Guest is not currently checked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guest.status = 'checked_out'
        guest.checked_out_at = timezone.now()
        guest.save()
        
        return Response(
            GuestSerializer(guest).data,
            status=status.HTTP_200_OK
        )


class AdminQRCodeCheckInView(APIView):
    """Admin endpoint to check-in guest using QR code verification code"""
    permission_classes = [IsAuthenticated]
    serializer_class = GuestCheckInSerializer
    
    @extend_schema(
        summary="Admin QR code guest check-in",
        description="Admin checks in guest using QR code verification code",
        tags=["Admin Guest Management"],
        request=GuestCheckInSerializer,
        responses={
            200: GuestSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    @transaction.atomic
    def post(self, request):
        """Admin check-in guest via QR code"""
        serializer = GuestCheckInSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        verification_code = serializer.validated_data['verification_code']
        
        try:
            guest = Guest.objects.select_related('booking__workspace').get(
                qr_code_verification_code=verification_code
            )
            workspace = guest.booking.workspace
            
            # Check if user is workspace admin/manager/staff
            if not check_workspace_member(request.user, workspace, ['staff', 'manager', 'admin']):
                return Response(
                    {'error': 'You do not have permission to perform this action'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if guest.status == 'checked_in':
            return Response(
                {'error': f'Guest {guest.first_name} is already checked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking = guest.booking
        now = timezone.now()
        
        guest.status = 'checked_in'
        guest.checked_in_at = now
        guest.checked_in_by = request.user
        guest.save()
        
        return Response(
            {
                **GuestSerializer(guest).data,
                'message': f'Guest {guest.first_name} checked in successfully'
            },
            status=status.HTTP_200_OK
        )


class AdminQRCodeCheckOutView(APIView):
    """Admin endpoint to check-out guest using QR code verification code"""
    permission_classes = [IsAuthenticated]
    serializer_class = GuestCheckOutSerializer
    
    @extend_schema(
        summary="Admin QR code guest check-out",
        description="Admin checks out guest using QR code verification code",
        tags=["Admin Guest Management"],
        request=GuestCheckOutSerializer,
        responses={
            200: GuestSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    @transaction.atomic
    def post(self, request):
        """Admin check-out guest via QR code"""
        serializer = GuestCheckOutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        verification_code = serializer.validated_data['verification_code']
        
        try:
            guest = Guest.objects.select_related('booking__workspace').get(
                qr_code_verification_code=verification_code
            )
            workspace = guest.booking.workspace
            
            # Check if user is workspace admin/manager/staff
            if not check_workspace_member(request.user, workspace, ['staff', 'manager', 'admin']):
                return Response(
                    {'error': 'You do not have permission to perform this action'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if guest.status != 'checked_in':
            return Response(
                {'error': f'Guest {guest.first_name} is not checked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guest.status = 'checked_out'
        guest.checked_out_at = timezone.now()
        guest.save()
        
        return Response(
            {
                **GuestSerializer(guest).data,
                'message': f'Guest {guest.first_name} checked out successfully'
            },
            status=status.HTTP_200_OK
        )
