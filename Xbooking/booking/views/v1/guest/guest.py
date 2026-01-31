"""
Guest Booking Views V1 - Guest Management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
from drf_spectacular.utils import extend_schema

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from booking.models import Booking, Guest
from booking.serializers.v1.guest import (
    GuestSerializer,
    AddGuestsSerializer,
    AddGuestsWithBookingSerializer,
    GuestCheckInSerializer,
    GuestCheckOutSerializer,
)


class GuestViewSet(CachedModelViewSet):
    """ViewSet for managing guests"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = GuestSerializer
    filterset_fields = ['status', 'booking']
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['created_at', 'checked_in_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get guests for user's bookings"""
        user = self.request.user
        return Guest.objects.filter(
            booking__user=user
        ).select_related('booking', 'booking__space')
    
    @extend_schema(
        request=AddGuestsSerializer,
        responses={201: GuestSerializer(many=True)}
    )
    @action(detail=False, methods=['post'], url_path='booking/(?P<booking_id>[^/.]+)/add')
    def add_to_booking(self, request, booking_id=None):
        """Add guests to a booking"""
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response(
                ErrorResponse(message='Booking not found or access denied'),
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AddGuestsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                ErrorResponse(message='Invalid data', errors=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guests_data = serializer.validated_data['guests']
        
        # Validate guest count
        existing_count = booking.guests.count()
        total_allowed = booking.number_of_guests
        
        if existing_count + len(guests_data) > total_allowed:
            return Response(
                ErrorResponse(
                    message=f'Cannot add {len(guests_data)} guests. '
                            f'Booking allows {total_allowed} total, '
                            f'already has {existing_count}.'
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create guests
        created_guests = []
        with transaction.atomic():
            for guest_data in guests_data:
                guest = Guest.objects.create(
                    booking=booking,
                    **guest_data
                )
                created_guests.append(guest)
        
        serializer = GuestSerializer(created_guests, many=True)
        return Response(
            SuccessResponse(
                data=serializer.data,
                message=f'Successfully added {len(created_guests)} guest(s)'
            ),
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        request=AddGuestsWithBookingSerializer,
        responses={201: GuestSerializer(many=True)}
    )
    @action(detail=False, methods=['post'])
    def add_guests(self, request):
        """Add guests to a booking (booking ID in request body)"""
        serializer = AddGuestsWithBookingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                ErrorResponse(message='Invalid data', errors=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking_id = serializer.validated_data['booking']
        guests_data = serializer.validated_data['guests']
        
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response(
                ErrorResponse(message='Booking not found or access denied'),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate guest count
        existing_count = booking.guests.count()
        total_allowed = booking.number_of_guests
        
        if existing_count + len(guests_data) > total_allowed:
            return Response(
                ErrorResponse(
                    message=f'Cannot add {len(guests_data)} guests. '
                            f'Booking allows {total_allowed} total, '
                            f'already has {existing_count}.'
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create guests
        created_guests = []
        with transaction.atomic():
            for guest_data in guests_data:
                guest = Guest.objects.create(
                    booking=booking,
                    **guest_data
                )
                created_guests.append(guest)
        
        serializer = GuestSerializer(created_guests, many=True)
        return Response(
            SuccessResponse(
                data=serializer.data,
                message=f'Successfully added {len(created_guests)} guest(s)'
            ),
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        request=GuestCheckInSerializer,
        responses={200: GuestSerializer}
    )
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Check in a guest"""
        guest = self.get_object()
        
        if guest.status == 'checked_in':
            return Response(
                ErrorResponse(message='Guest is already checked in'),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if guest.booking.status != 'confirmed':
            return Response(
                ErrorResponse(message='Booking must be confirmed before guest check-in'),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check in guest
        from django.utils import timezone
        guest.status = 'checked_in'
        guest.checked_in_at = timezone.now()
        guest.save()
        
        serializer = GuestSerializer(guest)
        return Response(
            SuccessResponse(
                data=serializer.data,
                message='Guest checked in successfully'
            )
        )
    
    @extend_schema(
        request=GuestCheckOutSerializer,
        responses={200: GuestSerializer}
    )
    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """Check out a guest"""
        guest = self.get_object()
        
        if guest.status != 'checked_in':
            return Response(
                ErrorResponse(message='Guest must be checked in before checkout'),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check out guest
        from django.utils import timezone
        guest.status = 'checked_out'
        guest.checked_out_at = timezone.now()
        guest.save()
        
        serializer = GuestSerializer(guest)
        return Response(
            SuccessResponse(
                data=serializer.data,
                message='Guest checked out successfully'
            )
        )


__all__ = ['GuestViewSet']
