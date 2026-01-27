"""
Cart Serializers V1
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from decimal import Decimal
from datetime import datetime

from booking.models import Cart, CartItem
from workspace.serializers.v1 import SpaceMinimalSerializer


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""
    space_details = SpaceMinimalSerializer(source='space', read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'space', 'space_details', 'booking_date', 'start_time',
            'end_time', 'check_in', 'check_out', 'booking_type',
            'number_of_guests', 'price', 'discount_amount', 'tax_amount',
            'special_requests', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart"""
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'items', 'subtotal', 'discount_total',
            'tax_total', 'total', 'item_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'subtotal', 'discount_total', 'tax_total',
            'total', 'created_at', 'updated_at'
        ]
    
    @extend_schema_field(serializers.IntegerField())
    def get_item_count(self, obj):
        """Get count of items in cart"""
        return obj.items.count()


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    space_id = serializers.UUIDField(required=True)
    slot_id = serializers.UUIDField(required=False, allow_null=True)
    booking_date = serializers.DateField(required=False, allow_null=True)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    booking_type = serializers.ChoiceField(
        choices=['hourly', 'daily', 'monthly'],
        default='daily'
    )
    number_of_guests = serializers.IntegerField(min_value=1, default=1)
    special_requests = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )
    
    def validate(self, data):
        """Validate either slot_id OR explicit date+times provided"""
        slot_id = data.get('slot_id')
        booking_date = data.get('booking_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        # Must provide either slot_id or all date/time fields
        if slot_id:
            return data
        
        if not all([booking_date, start_time, end_time]):
            raise serializers.ValidationError(
                'Provide either slot_id or booking_date + start_time + end_time'
            )
        
        # Validate times
        check_in = datetime.combine(booking_date, start_time)
        check_out = datetime.combine(booking_date, end_time)
        
        if check_in >= check_out:
            raise serializers.ValidationError('End time must be after start time')
        
        return data


class RemoveFromCartSerializer(serializers.Serializer):
    """Serializer for removing items from cart"""
    cart_item_id = serializers.UUIDField(required=True)


class CheckoutSerializer(serializers.Serializer):
    """Serializer for cart checkout"""
    payment_method = serializers.ChoiceField(
        choices=['card', 'bank_transfer', 'paystack', 'wallet'],
        required=False,
        default='wallet',
        help_text='Payment method (defaults to wallet)'
    )
    cart_item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text='Specific cart items to checkout (optional, defaults to all)'
    )
