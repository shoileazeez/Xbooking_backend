"""
Booking Serializers V1
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from booking.models import Booking
from workspace.serializers.v1 import SpaceMinimalSerializer
from user.serializers.v1 import UserMinimalSerializer


class QRCodeMinimalSerializer(serializers.Serializer):
    """Minimal QR code serializer for booking details"""
    id = serializers.UUIDField(read_only=True)
    qr_code_image_url = serializers.URLField(read_only=True)
    verification_code = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    scan_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class BookingSerializer(serializers.ModelSerializer):
    """Base booking serializer"""
    space_details = SpaceMinimalSerializer(source='space', read_only=True)
    user_details = UserMinimalSerializer(source='user', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    days_used = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'workspace', 'workspace_name', 'space', 'space_details',
            'user', 'user_details', 'booking_type', 'booking_date',
            'start_time', 'end_time', 'check_in', 'check_out',
            'number_of_guests', 'base_price', 'discount_amount',
            'tax_amount', 'total_price', 'status', 'special_requests',
            'is_checked_in', 'is_checked_out', 'days_used', 'days_remaining',
            'created_at', 'updated_at', 'confirmed_at', 'cancelled_at'
        ]
        read_only_fields = [
            'id', 'workspace', 'workspace_name', 'user', 'base_price',
            'discount_amount', 'tax_amount', 'total_price', 'status',
            'is_checked_in', 'is_checked_out', 'created_at', 'updated_at',
            'confirmed_at', 'cancelled_at'
        ]
    
    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_days_used(self, obj):
        """Return days used for monthly bookings"""
        if obj.booking_type == 'monthly':
            return obj.days_used
        return None
    
    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_days_remaining(self, obj):
        """Return days remaining for monthly bookings"""
        if obj.booking_type == 'monthly':
            return obj.days_remaining
        return None


class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for booking list views (minimal data)"""
    space_name = serializers.CharField(source='space.name', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'workspace_name', 'space_name', 'booking_type',
            'booking_date', 'start_time', 'end_time', 'total_price',
            'status', 'is_checked_in', 'is_checked_out', 'created_at'
        ]
        read_only_fields = fields


class BookingDetailSerializer(BookingSerializer):
    """Detailed booking serializer with all information"""
    guest_count = serializers.SerializerMethodField()
    has_review = serializers.SerializerMethodField()
    qr_code = serializers.SerializerMethodField()
    
    class Meta(BookingSerializer.Meta):
        fields = BookingSerializer.Meta.fields + ['guest_count', 'has_review', 'qr_code']
    
    @extend_schema_field(serializers.IntegerField())
    def get_guest_count(self, obj):
        """Get count of guests for this booking"""
        return obj.guests.count()
    
    @extend_schema_field(serializers.BooleanField())
    def get_has_review(self, obj):
        """Check if booking has a review"""
        return hasattr(obj, 'review')
    
    @extend_schema_field(QRCodeMinimalSerializer(allow_null=True))
    def get_qr_code(self, obj):
        """Get QR code details if available"""
        if hasattr(obj, 'qr_code') and obj.qr_code:
            return QRCodeMinimalSerializer(obj.qr_code).data
        return None


class CreateBookingSerializer(serializers.Serializer):
    """Serializer for creating a booking from cart checkout"""
    cart_item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text='List of cart item IDs to convert to bookings'
    )
    payment_method = serializers.ChoiceField(
        choices=['card', 'bank_transfer', 'paystack'],
        required=True
    )
    
    def validate_cart_item_ids(self, value):
        """Validate cart items exist and belong to user"""
        if not value:
            raise serializers.ValidationError('At least one cart item is required')
        return value


class DirectBookingSerializer(serializers.Serializer):
    """Serializer for creating a direct booking without cart"""
    space_id = serializers.UUIDField(required=True, help_text='Space ID to book')
    booking_date = serializers.DateField(required=True, help_text='Booking date')
    start_time = serializers.TimeField(required=True, help_text='Start time')
    end_time = serializers.TimeField(required=True, help_text='End time')
    booking_type = serializers.ChoiceField(
        choices=['hourly', 'daily', 'monthly'],
        default='hourly',
        help_text='Type of booking'
    )
    number_of_guests = serializers.IntegerField(
        default=1,
        min_value=1,
        help_text='Number of guests'
    )
    special_requests = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Special requests or notes'
    )
    
    def validate(self, data):
        """Validate booking times"""
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError('End time must be after start time')
        return data


class CancelBookingSerializer(serializers.Serializer):
    """Serializer for cancelling a booking"""
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Reason for cancellation'
    )
