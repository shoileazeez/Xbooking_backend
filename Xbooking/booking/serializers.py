"""
Booking and Cart Serializers
"""
from rest_framework import serializers
from booking.models import Booking, Cart, CartItem, BookingReview
from workspace.models import Space
from workspace.serializers.workspace import SpaceSimpleSerializer
from drf_spectacular.utils import extend_schema_field
from decimal import Decimal


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""
    space_details = SpaceSimpleSerializer(source='space', read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'space', 'space_details', 'check_in', 'check_out', 'number_of_guests', 
                  'price', 'discount_amount', 'tax_amount', 'special_requests', 'added_at', 'updated_at']
        read_only_fields = ['id', 'added_at', 'updated_at']


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart"""
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'subtotal', 'discount_total', 
                  'tax_total', 'total', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'subtotal', 'discount_total', 
                           'tax_total', 'total', 'created_at', 'updated_at']
    
    @extend_schema_field(serializers.IntegerField())
    def get_item_count(self, obj):
        """Get count of items in cart"""
        return obj.items.count()


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    space_id = serializers.CharField(required=True)
    # Accept either a slot_id OR explicit booking_date + start_time/end_time
    slot_id = serializers.CharField(required=False, allow_blank=True)
    booking_date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    booking_type = serializers.ChoiceField(choices=['hourly', 'daily', 'monthly'], default='hourly')
    number_of_guests = serializers.IntegerField(min_value=1, default=1)
    special_requests = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        # Validate either slot_id provided OR explicit date+times
        slot = data.get('slot_id')
        booking_date = data.get('booking_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if slot:
            return data

        if not (booking_date and start_time and end_time):
            raise serializers.ValidationError("Provide either slot_id or booking_date + start_time + end_time")

        from datetime import datetime
        if datetime.combine(booking_date, start_time) >= datetime.combine(booking_date, end_time):
            raise serializers.ValidationError("End time must be after start time")
        return data


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for bookings"""
    space_name = serializers.CharField(source='space.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    days_used = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = ['id', 'workspace', 'space', 'space_name', 'user', 'user_email', 
                  'booking_type', 'check_in', 'check_out', 'number_of_guests',
                  'base_price', 'discount_amount', 'tax_amount', 'total_price',
                  'status', 'special_requests', 'days_used', 'days_remaining',
                  'created_at', 'confirmed_at', 'cancelled_at']
        read_only_fields = ['id', 'workspace', 'user', 'base_price', 'discount_amount', 
                           'tax_amount', 'total_price', 'created_at', 'confirmed_at', 'cancelled_at']
    
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


class CreateBookingSerializer(serializers.Serializer):
    """Serializer for creating bookings from cart or direct"""
    space_id = serializers.CharField(required=True)
    slot_id = serializers.CharField(required=False, allow_blank=True)
    booking_date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    booking_type = serializers.ChoiceField(choices=['hourly', 'daily', 'monthly'], default='daily')
    number_of_guests = serializers.IntegerField(min_value=1, default=1)
    special_requests = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        # Validate either slot_id provided OR explicit date+times
        slot = data.get('slot_id')
        booking_date = data.get('booking_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if slot:
            return data

        if not (booking_date and start_time and end_time):
            raise serializers.ValidationError("Provide either slot_id or booking_date + start_time + end_time")

        from datetime import datetime
        if datetime.combine(booking_date, start_time) >= datetime.combine(booking_date, end_time):
            raise serializers.ValidationError("End time must be after start time")
        return data
        return data


class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for listing bookings"""
    space_name = serializers.CharField(source='space.name', read_only=True)
    branch_name = serializers.CharField(source='space.branch.name', read_only=True)
    
    class Meta:
        model = Booking
        fields = ['id', 'space', 'space_name', 'branch_name', 'booking_type', 
                  'check_in', 'check_out', 'status', 'total_price', 'created_at']
        read_only_fields = fields


class BookingDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for booking"""
    space_details = SpaceSimpleSerializer(source='space', read_only=True)
    user_details = serializers.SerializerMethodField()
    days_used = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    qr_code_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = ['id', 'workspace', 'space_details', 'user_details', 'booking_type',
                  'check_in', 'check_out', 'number_of_guests', 'base_price', 
                  'discount_amount', 'tax_amount', 'total_price', 'status',
                  'special_requests', 'days_used', 'days_remaining', 'qr_code_stats',
                  'created_at', 'confirmed_at', 'cancelled_at']
        read_only_fields = fields
    
    @extend_schema_field(serializers.DictField())
    def get_user_details(self, obj):
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'full_name': obj.user.full_name,
            'avatar_url': obj.user.avatar_url
        }
    
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
    
    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_qr_code_stats(self, obj):
        """Return QR code statistics if QR code exists"""
        if hasattr(obj, 'qr_code') and obj.qr_code:
            qr_code = obj.qr_code
            return {
                'qr_code_id': str(qr_code.id),
                'status': qr_code.status,
                'scan_count': qr_code.scan_count,
                'total_check_ins': qr_code.total_check_ins,
                'max_check_ins': qr_code.max_check_ins or qr_code.calculate_max_check_ins(),
                'expires_at': qr_code.expires_at,
                'sent_at': qr_code.sent_at
            }
        return None


class CancelBookingSerializer(serializers.Serializer):
    """Serializer for cancelling bookings"""
    cancellation_reason = serializers.CharField(required=False, allow_blank=True)


class BookingReviewSerializer(serializers.ModelSerializer):
    """Serializer for booking reviews"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    space_name = serializers.CharField(source='space.name', read_only=True)
    
    class Meta:
        model = BookingReview
        fields = ['id', 'booking', 'user_name', 'space_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'booking', 'user_name', 'space_name', 'created_at']


class CreateReviewSerializer(serializers.Serializer):
    """Serializer for creating reviews"""
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    comment = serializers.CharField(required=False, allow_blank=True)


class CheckoutSerializer(serializers.Serializer):
    """Serializer for cart checkout"""
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)



