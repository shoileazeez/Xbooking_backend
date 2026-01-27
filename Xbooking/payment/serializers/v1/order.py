"""
Payment V1 Serializers - Order Management
"""
from rest_framework import serializers
from payment.models import Order
from booking.serializers.v1 import BookingListSerializer


class OrderSerializer(serializers.ModelSerializer):
    """Detailed order serializer"""
    bookings = BookingListSerializer(many=True, read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'workspace', 'workspace_name',
            'user', 'user_email', 'bookings',
            'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
            'status', 'payment_method', 'payment_reference',
            'notes', 'created_at', 'updated_at',
            'paid_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at',
            'paid_at', 'completed_at', 'payment_reference'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Optimized serializer for order lists"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    booking_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'workspace', 'workspace_name',
            'booking_count', 'total_amount', 'status',
            'payment_method', 'created_at', 'paid_at'
        ]
        read_only_fields = fields
    
    def get_booking_count(self, obj):
        return obj.bookings.count()


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    booking_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of booking IDs to include in the order"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes for the order"
    )
    
    def validate_booking_ids(self, value):
        """Ensure booking IDs are unique"""
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate booking IDs are not allowed")
        return value


__all__ = [
    'OrderSerializer',
    'OrderListSerializer',
    'CreateOrderSerializer',
]
