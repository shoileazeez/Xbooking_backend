"""
Calendar and Slot Serializers for v1 API
"""
from rest_framework import serializers
from workspace.models import SpaceCalendar, SpaceCalendarSlot, Space
from datetime import datetime, date


class SpaceCalendarSerializer(serializers.ModelSerializer):
    """Serializer for Space Calendar"""
    space_name = serializers.CharField(source='space.name', read_only=True)
    
    class Meta:
        model = SpaceCalendar
        fields = [
            'id', 'space', 'space_name', 'time_interval_minutes',
            'operating_hours', 'hourly_enabled', 'daily_enabled',
            'monthly_enabled', 'hourly_price', 'daily_price',
            'monthly_price', 'min_advance_booking_days',
            'max_advance_booking_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SpaceCalendarSlotSerializer(serializers.ModelSerializer):
    """Serializer for Space Calendar Slot"""
    space = serializers.SerializerMethodField()
    
    class Meta:
        model = SpaceCalendarSlot
        fields = [
            'id', 'calendar', 'space', 'date', 'start_time',
            'end_time', 'booking_type', 'status', 'booking'
        ]
        read_only_fields = ['id']
    
    def get_space(self, obj):
        return {
            'id': str(obj.calendar.space.id),
            'name': obj.calendar.space.name,
            'space_type': obj.calendar.space.space_type
        }


class CheckAvailabilitySerializer(serializers.Serializer):
    """Serializer for checking space availability"""
    space = serializers.UUIDField(required=True, help_text="Space UUID")
    booking_type = serializers.ChoiceField(
        choices=['hourly', 'daily', 'monthly'],
        required=True,
        help_text="Type of booking"
    )
    date = serializers.DateField(
        required=True,
        help_text="Booking date (YYYY-MM-DD)"
    )
    start_time = serializers.TimeField(
        required=False,
        allow_null=True,
        help_text="Start time for hourly bookings (HH:MM)"
    )
    end_time = serializers.TimeField(
        required=False,
        allow_null=True,
        help_text="End time for hourly bookings (HH:MM)"
    )
    
    def validate_date(self, value):
        """Ensure date is not in the past"""
        if value < date.today():
            raise serializers.ValidationError("Cannot book for past dates")
        return value
    
    def validate(self, attrs):
        """Validate time fields for hourly bookings"""
        booking_type = attrs.get('booking_type')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if booking_type == 'hourly':
            if not start_time or not end_time:
                raise serializers.ValidationError({
                    "time": "start_time and end_time are required for hourly bookings"
                })
            
            if start_time >= end_time:
                raise serializers.ValidationError({
                    "time": "end_time must be after start_time"
                })
        
        return attrs


class AvailableSlotsSerializer(serializers.Serializer):
    """Serializer for available slots response"""
    space = serializers.UUIDField()
    space_name = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    availability = serializers.ListField(child=serializers.DictField())
