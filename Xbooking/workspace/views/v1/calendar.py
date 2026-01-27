"""
Space Calendar and Slot ViewSets for v1 API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, date, time, timedelta
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from core.views import CachedModelViewSet
from core.pagination import StandardResultsSetPagination
from workspace.models import Space, SpaceCalendar, SpaceCalendarSlot
from workspace.serializers.v1.calendar import (
    SpaceCalendarSerializer,
    SpaceCalendarSlotSerializer,
    CheckAvailabilitySerializer,
    AvailableSlotsSerializer
)


@extend_schema_view(
    list=extend_schema(description="List space calendars"),
    retrieve=extend_schema(description="Get calendar details"),
)
class PublicSpaceCalendarViewSet(CachedModelViewSet):
    """Public read-only space calendar listing"""
    serializer_class = SpaceCalendarSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get', 'post', 'head', 'options']
    cache_timeout = 300
    
    def get_queryset(self):
        queryset = SpaceCalendar.objects.filter(
            space__is_available=True,
            space__branch__is_active=True,
            space__branch__workspace__is_active=True
        ).select_related('space', 'space__branch', 'space__branch__workspace')
        
        # Filter by space if provided
        space_id = self.request.query_params.get('space')
        if space_id:
            queryset = queryset.filter(space_id=space_id)
        
        return queryset


@extend_schema_view(
    list=extend_schema(
        description="List available slots for a space",
        parameters=[
            OpenApiParameter(name='space', description='Filter by space ID', required=False, type=str),
            OpenApiParameter(name='date', description='Filter by date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='booking_type', description='Filter by booking type (hourly/daily/monthly)', required=False, type=str),
            OpenApiParameter(name='status', description='Filter by status (available/booked)', required=False, type=str),
        ]
    ),
    retrieve=extend_schema(description="Get slot details"),
)
class PublicSpaceSlotViewSet(CachedModelViewSet):
    """Public read-only space slot listing"""
    serializer_class = SpaceCalendarSlotSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get', 'post']  # Allow POST for check_availability
    cache_timeout = 60  # Short cache for slots (1 minute)
    
    def get_queryset(self):
        queryset = SpaceCalendarSlot.objects.filter(
            calendar__space__is_available=True,
            calendar__space__branch__is_active=True,
            calendar__space__branch__workspace__is_active=True
        ).select_related('calendar', 'calendar__space', 'booking')
        
        # Filter by space
        space_id = self.request.query_params.get('space')
        if space_id:
            queryset = queryset.filter(calendar__space_id=space_id)
        
        # Filter by date
        slot_date = self.request.query_params.get('date')
        if slot_date:
            try:
                queryset = queryset.filter(date=slot_date)
            except ValueError:
                pass
        
        # Filter by booking type
        booking_type = self.request.query_params.get('booking_type')
        if booking_type in ['hourly', 'daily', 'monthly']:
            queryset = queryset.filter(booking_type=booking_type)
        
        # Filter by status
        slot_status = self.request.query_params.get('status')
        if slot_status in ['available', 'booked']:
            queryset = queryset.filter(status=slot_status)
        
        # Only show future slots by default
        today = date.today()
        queryset = queryset.filter(date__gte=today)
        
        return queryset.order_by('date', 'start_time')
    
    @extend_schema(
        description="Check if a space is available for specific date/time",
        request=CheckAvailabilitySerializer,
        responses={200: {
            "type": "object",
            "properties": {
                "available": {"type": "boolean"},
                "message": {"type": "string"},
                "conflicting_slots": {"type": "array"}
            }
        }}
    )
    @action(detail=False, methods=['post'], url_path='check-availability')
    def check_availability(self, request):
        """
        Check if space is available for booking
        
        POST body:
        {
            "space": "space_uuid",
            "booking_type": "hourly|daily|monthly",
            "date": "2026-01-15",
            "start_time": "09:00",  # For hourly
            "end_time": "12:00"      # For hourly
        }
        """
        serializer = CheckAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        space_id = serializer.validated_data['space']
        booking_type = serializer.validated_data['booking_type']
        check_date = serializer.validated_data['date']
        start_time = serializer.validated_data.get('start_time')
        end_time = serializer.validated_data.get('end_time')
        
        # Get space
        try:
            space = Space.objects.get(id=space_id, is_available=True)
        except Space.DoesNotExist:
            return Response(
                {"available": False, "message": "Space not found or not available"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get calendar
        try:
            calendar = SpaceCalendar.objects.get(space=space)
        except SpaceCalendar.DoesNotExist:
            return Response(
                {"available": False, "message": "Calendar not configured for this space"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if booking type is enabled
        if booking_type == 'hourly' and not calendar.hourly_enabled:
            return Response(
                {"available": False, "message": "Hourly booking not enabled for this space"},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif booking_type == 'daily' and not calendar.daily_enabled:
            return Response(
                {"available": False, "message": "Daily booking not enabled for this space"},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif booking_type == 'monthly' and not calendar.monthly_enabled:
            return Response(
                {"available": False, "message": "Monthly booking not enabled for this space"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Query slots
        slots = SpaceCalendarSlot.objects.filter(
            calendar=calendar,
            date=check_date,
            booking_type=booking_type
        )
        
        # For hourly bookings, check specific time range
        if booking_type == 'hourly':
            if not start_time or not end_time:
                return Response(
                    {"available": False, "message": "start_time and end_time required for hourly bookings"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            slots = slots.filter(
                start_time__gte=start_time,
                end_time__lte=end_time
            )
        
        # Check if any slots are booked or reserved (not available)
        unavailable_slots = slots.exclude(status='available')
        
        if unavailable_slots.exists():
            return Response({
                "available": False,
                "message": "Space is not available for the selected time",
                "conflicting_slots": SpaceCalendarSlotSerializer(unavailable_slots, many=True).data
            })
        
        # Check if slots exist
        if not slots.exists():
            return Response({
                "available": False,
                "message": "No slots found for the selected date/time"
            })
        
        return Response({
            "available": True,
            "message": "Space is available",
            "available_slots": SpaceCalendarSlotSerializer(slots.filter(status='available'), many=True).data
        })
    
    @extend_schema(
        description="Get available slots for a space within a date range",
        parameters=[
            OpenApiParameter(name='space', description='Space ID', required=True, type=str),
            OpenApiParameter(name='start_date', description='Start date (YYYY-MM-DD)', required=True, type=str),
            OpenApiParameter(name='end_date', description='End date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='booking_type', description='Booking type (hourly/daily/monthly)', required=False, type=str),
        ],
        responses={200: AvailableSlotsSerializer}
    )
    @action(detail=False, methods=['get'], url_path='available')
    def get_available_slots(self, request):
        """
        Get all available slots for a space
        
        Query params:
        - space: space_uuid (required)
        - start_date: YYYY-MM-DD (required)
        - end_date: YYYY-MM-DD (optional, defaults to start_date + 30 days)
        - booking_type: hourly|daily|monthly (optional)
        """
        space_id = request.query_params.get('space')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        booking_type = request.query_params.get('booking_type')
        
        # Validate required params
        if not space_id:
            return Response(
                {"error": "space parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not start_date_str:
            return Response(
                {"error": "start_date parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid start_date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid end_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            end_date = start_date + timedelta(days=30)
        
        # Get space
        try:
            space = Space.objects.get(id=space_id, is_available=True)
        except Space.DoesNotExist:
            return Response(
                {"error": "Space not found or not available"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get slots
        slots = SpaceCalendarSlot.objects.filter(
            calendar__space=space,
            date__gte=start_date,
            date__lte=end_date,
            status='available'
        ).select_related('calendar')
        
        # Filter by booking type if provided
        if booking_type and booking_type in ['hourly', 'daily', 'monthly']:
            slots = slots.filter(booking_type=booking_type)
        
        # Group by date and booking type
        grouped_slots = {}
        for slot in slots:
            date_key = slot.date.isoformat()
            if date_key not in grouped_slots:
                grouped_slots[date_key] = {
                    'date': date_key,
                    'hourly_slots': [],
                    'daily_slots': [],
                    'monthly_slots': []
                }
            
            slot_data = SpaceCalendarSlotSerializer(slot).data
            
            if slot.booking_type == 'hourly':
                grouped_slots[date_key]['hourly_slots'].append(slot_data)
            elif slot.booking_type == 'daily':
                grouped_slots[date_key]['daily_slots'].append(slot_data)
            elif slot.booking_type == 'monthly':
                grouped_slots[date_key]['monthly_slots'].append(slot_data)
        
        return Response({
            "space": space.id,
            "space_name": space.name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "availability": list(grouped_slots.values())
        })
