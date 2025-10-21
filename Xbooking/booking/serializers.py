"""
Booking and Cart Serializers
"""
from rest_framework import serializers
from booking.models import Booking, Cart, CartItem, BookingReview, Guest
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
        fields = ['id', 'user', 'workspace', 'items', 'subtotal', 'discount_total', 
                  'tax_total', 'total', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'workspace', 'subtotal', 'discount_total', 
                           'tax_total', 'total', 'created_at', 'updated_at']
    
    @extend_schema_field(serializers.IntegerField())
    def get_item_count(self, obj):
        """Get count of items in cart"""
        return obj.items.count()


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    space_id = serializers.CharField(required=True)
    check_in = serializers.DateTimeField(required=True)
    check_out = serializers.DateTimeField(required=True)
    number_of_guests = serializers.IntegerField(min_value=1, default=1)
    special_requests = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data['check_in'] >= data['check_out']:
            raise serializers.ValidationError("Check-out must be after check-in")
        return data


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for bookings"""
    space_name = serializers.CharField(source='space.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Booking
        fields = ['id', 'workspace', 'space', 'space_name', 'user', 'user_email', 
                  'booking_type', 'check_in', 'check_out', 'number_of_guests',
                  'base_price', 'discount_amount', 'tax_amount', 'total_price',
                  'status', 'special_requests', 'created_at', 'confirmed_at', 'cancelled_at']
        read_only_fields = ['id', 'workspace', 'user', 'base_price', 'discount_amount', 
                           'tax_amount', 'total_price', 'created_at', 'confirmed_at', 'cancelled_at']


class CreateBookingSerializer(serializers.Serializer):
    """Serializer for creating bookings from cart or direct"""
    space_id = serializers.CharField(required=True)
    check_in = serializers.DateTimeField(required=True)
    check_out = serializers.DateTimeField(required=True)
    booking_type = serializers.ChoiceField(choices=['hourly', 'daily', 'monthly'], default='daily')
    number_of_guests = serializers.IntegerField(min_value=1, default=1)
    special_requests = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data['check_in'] >= data['check_out']:
            raise serializers.ValidationError("Check-out must be after check-in")
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
    
    class Meta:
        model = Booking
        fields = ['id', 'workspace', 'space_details', 'user_details', 'booking_type',
                  'check_in', 'check_out', 'number_of_guests', 'base_price', 
                  'discount_amount', 'tax_amount', 'total_price', 'status',
                  'special_requests', 'created_at', 'confirmed_at', 'cancelled_at']
        read_only_fields = fields
    
    @extend_schema_field(serializers.DictField())
    def get_user_details(self, obj):
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'full_name': obj.user.full_name,
            'avatar_url': obj.user.avatar_url
        }


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


class GuestSerializer(serializers.ModelSerializer):
    """Serializer for booking guests"""
    booking_id = serializers.CharField(source='booking.id', read_only=True)
    verified_by_email = serializers.CharField(source='verified_by.email', read_only=True, allow_null=True)
    checked_in_by_email = serializers.CharField(source='checked_in_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Guest
        fields = [
            'id', 'booking_id', 'first_name', 'last_name', 'email', 'phone',
            'status', 'verification_status', 'verified_by_email', 'verified_at',
            'rejection_reason', 'qr_code_sent', 'qr_code_sent_at',
            'qr_code_verification_code', 'checked_in_at', 'checked_out_at',
            'checked_in_by_email', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'booking_id', 'qr_code_verification_code', 'verified_by_email',
            'verified_at', 'qr_code_sent', 'qr_code_sent_at', 'checked_in_at',
            'checked_out_at', 'checked_in_by_email', 'created_at', 'updated_at'
        ]


class CreateGuestSerializer(serializers.Serializer):
    """Serializer for adding guests to a booking"""
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    class Meta:
        fields = ['first_name', 'last_name', 'email', 'phone']
