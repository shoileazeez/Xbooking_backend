"""
Booking Views V1
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db import transaction

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from booking.models import Booking
from booking.serializers.v1 import (
    BookingSerializer,
    BookingListSerializer,
    BookingDetailSerializer,
    CancelBookingSerializer,
    DirectBookingSerializer
)
from booking.services import BookingService
from workspace.models import Space
from decimal import Decimal
from datetime import datetime


@extend_schema_view(
    list=extend_schema(description="List user bookings"),
    retrieve=extend_schema(description="Retrieve booking details"),
    create=extend_schema(description="Create booking (from cart checkout)"),
)
class BookingViewSet(CachedModelViewSet):
    """ViewSet for managing bookings"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300
    http_method_names = ['get', 'post', 'delete']
    
    @action(detail=False, methods=['get'])
    def past(self, request):
        """Get past/completed bookings for current user"""
        qs = self.get_queryset().filter(status__in=['completed', 'cancelled'])
        serializer = BookingListSerializer(qs, many=True)
        return SuccessResponse(data=serializer.data)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        elif self.action == 'retrieve':
            return BookingDetailSerializer
        return BookingSerializer
    
    def get_queryset(self):
        user = self.request.user
        return Booking.objects.filter(
            user=user
        ).select_related(
            'workspace', 'space', 'user'
        ).prefetch_related('guests').order_by('-created_at')
    
    def list(self, request):
        """List user bookings"""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(
            message='Bookings retrieved successfully',
            data=serializer.data
        )
    
    def retrieve(self, request, pk=None):
        """Get booking details"""
        booking = self.get_object()
        serializer = self.get_serializer(booking)
        return SuccessResponse(
            message='Booking retrieved successfully',
            data=serializer.data
        )
    
    @extend_schema(
        request=DirectBookingSerializer,
        responses={201: BookingDetailSerializer}
    )
    def create(self, request):
        """Create a direct booking without cart"""
        serializer = DirectBookingSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid booking data',
                errors=serializer.errors,
                status_code=400
            )
        
        data = serializer.validated_data
        
        try:
            # Get space
            space = Space.objects.select_related('branch__workspace').get(
                id=data['space_id']
            )
            
            # Combine date and time to create check_in and check_out
            check_in = datetime.combine(data['booking_date'], data['start_time'])
            check_out = datetime.combine(data['booking_date'], data['end_time'])
            
            # Calculate price
            hours = (check_out - check_in).total_seconds() / 3600
            base_price = Decimal(str(space.price_per_hour)) * Decimal(str(hours))
            
            # Create reservation first (15-minute hold)
            with transaction.atomic():
                reservation = BookingService.create_reservation(
                    space=space,
                    user=request.user,
                    start_datetime=check_in,
                    end_datetime=check_out,
                    expiry_minutes=15
                )
                
                # Create booking directly as pending (requires payment)
                booking = Booking.objects.create(
                    workspace=space.branch.workspace,
                    space=space,
                    user=request.user,
                    booking_type=data['booking_type'],
                    booking_date=data['booking_date'],
                    start_time=data['start_time'],
                    end_time=data['end_time'],
                    check_in=check_in,
                    check_out=check_out,
                    number_of_guests=data['number_of_guests'],
                    base_price=base_price,
                    total_price=base_price,
                    special_requests=data.get('special_requests', ''),
                    status='pending'
                )
            
            serializer = BookingDetailSerializer(booking)
            return SuccessResponse(
                message='Booking created successfully. Complete payment within 15 minutes.',
                data=serializer.data,
                status_code=201
            )
            
        except Space.DoesNotExist:
            return ErrorResponse(
                message='Space not found',
                status_code=404
            )
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=409
            )
        except Exception as e:
            return ErrorResponse(
                message=f'Failed to create booking: {str(e)}',
                status_code=500
            )
    
    @extend_schema(
        request=CancelBookingSerializer,
        responses={200: BookingDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        
        serializer = CancelBookingSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid cancellation request',
                errors=serializer.errors,
                status_code=400
            )
        
        reason = serializer.validated_data.get('reason')
        
        try:
            # Cancel booking via service
            BookingService.cancel_booking(
                booking=booking,
                cancelled_by=request.user,
                reason=reason
            )
            
            serializer = BookingDetailSerializer(booking)
            return SuccessResponse(
                message='Booking cancelled successfully',
                data=serializer.data
            )
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
    
    @extend_schema(
        responses={200: BookingDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Check in to a booking"""
        booking = self.get_object()
        
        try:
            # Check in via service
            BookingService.check_in_booking(
                booking=booking,
                checked_in_by=request.user
            )
            
            serializer = BookingDetailSerializer(booking)
            return SuccessResponse(
                message='Checked in successfully',
                data=serializer.data
            )
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
    
    @extend_schema(
        responses={200: BookingDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """Check out from a booking"""
        booking = self.get_object()
        
        try:
            # Check out via service
            BookingService.check_out_booking(
                booking=booking,
                checked_out_by=request.user
            )
            
            serializer = BookingDetailSerializer(booking)
            return SuccessResponse(
                message='Checked out successfully',
                data=serializer.data
            )
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
    
    @extend_schema(
        responses={200: BookingListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming confirmed bookings (today and future)"""
        from django.utils import timezone
        from django.db.models import Q
        import logging
        
        logger = logging.getLogger(__name__)
        
        now = timezone.now()
        today = now.date()
        
        # Debug logging
        all_bookings = self.get_queryset()
        logger.info(f"Total bookings for user: {all_bookings.count()}")
        logger.info(f"Today's date: {today}")
        
        confirmed_bookings = all_bookings.filter(status='confirmed')
        logger.info(f"Confirmed bookings: {confirmed_bookings.count()}")
        
        for booking in confirmed_bookings:
            logger.info(f"Booking ID: {booking.id}, Date: {booking.booking_date}, Status: {booking.status}, Checked out: {booking.is_checked_out}")
        
        # Get bookings that are:
        # 1. Confirmed status
        # 2. Either booking_date is today or in future
        bookings = all_bookings.filter(
            status='confirmed'
        ).filter(
            Q(booking_date__gte=today) |  # Future bookings
            Q(booking_date=today, is_checked_out=False)  # Today's bookings not checked out
        ).order_by('booking_date', 'start_time')
        
        logger.info(f"Upcoming bookings count: {bookings.count()}")
        
        page = self.paginate_queryset(bookings)
        if page is not None:
            serializer = BookingListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = BookingListSerializer(bookings, many=True)
        return SuccessResponse(
            message='Upcoming bookings retrieved successfully',
            data=serializer.data
        )
    
    @extend_schema(
        responses={200: BookingListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def past(self, request):
        """Get past bookings"""
        from django.utils import timezone
        
        bookings = self.get_queryset().filter(
            check_out__lt=timezone.now()
        ).order_by('-check_out')
        
        page = self.paginate_queryset(bookings)
        if page is not None:
            serializer = BookingListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = BookingListSerializer(bookings, many=True)
        return SuccessResponse(
            message='Past bookings retrieved successfully',
            data=serializer.data
        )
