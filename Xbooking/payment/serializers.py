"""
Payment and Order Serializers
"""
from rest_framework import serializers
from payment.models import Order, Payment, PaymentWebhook, Refund
from booking.models import Booking
from booking.serializers import BookingListSerializer
from drf_spectacular.utils import extend_schema_field
from decimal import Decimal


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders"""
    bookings = BookingListSerializer(many=True, read_only=True)
    booking_ids = serializers.PrimaryKeyRelatedField(
        queryset=Booking.objects.all(),
        many=True,
        write_only=True,
        source='bookings'
    )
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'workspace', 'user', 'bookings', 'booking_ids',
            'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
            'status', 'payment_method', 'payment_reference', 'notes',
            'created_at', 'updated_at', 'paid_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'workspace', 'user', 'bookings',
            'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
            'created_at', 'updated_at', 'paid_at', 'completed_at'
        ]


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating orders from bookings"""
    booking_ids = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        help_text="List of booking IDs to include in this order"
    )
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0'), required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_booking_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one booking is required")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments"""
    order_details = OrderSerializer(source='order', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_details', 'workspace', 'user', 'amount',
            'currency', 'payment_method', 'gateway_transaction_id', 'status',
            'gateway_response', 'retry_count', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'order', 'workspace', 'user', 'gateway_response',
            'retry_count', 'created_at', 'updated_at', 'completed_at'
        ]


class InitiatePaymentSerializer(serializers.Serializer):
    """Serializer for initiating payment"""
    order_id = serializers.CharField(required=True)
    payment_method = serializers.ChoiceField(
        choices=['paystack', 'flutterwave', 'stripe', 'paypal', 'bank_transfer'],
        required=True
    )
    email = serializers.EmailField(required=False)  # For payment gateway
    phone = serializers.CharField(required=False)  # For payment gateway


class PaymentCallbackSerializer(serializers.Serializer):
    """Serializer for payment gateway callbacks"""
    reference = serializers.CharField(required=True)  # Paystack reference
    status = serializers.CharField(required=True)
    message = serializers.CharField(required=False, allow_blank=True)


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refunds"""
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'order', 'workspace', 'user', 'amount',
            'reason', 'reason_description', 'gateway_refund_id', 'status',
            'requested_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'payment', 'order', 'workspace', 'user', 'gateway_refund_id',
            'status', 'requested_at', 'completed_at'
        ]


class CreateRefundSerializer(serializers.Serializer):
    """Serializer for requesting refunds"""
    order_id = serializers.CharField(required=True)
    reason = serializers.ChoiceField(
        choices=['user_request', 'booking_cancelled', 'system_error', 'duplicate_charge', 'other'],
        required=True
    )
    reason_description = serializers.CharField(required=True)
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0.01'), required=False
    )


class PaymentWebhookSerializer(serializers.ModelSerializer):
    """Serializer for payment webhooks"""
    
    class Meta:
        model = PaymentWebhook
        fields = [
            'id', 'payment_method', 'gateway_event_id', 'payload',
            'status', 'error_message', 'received_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'status', 'error_message', 'received_at', 'processed_at'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for listing orders"""
    booking_count = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user_email', 'booking_count',
            'total_amount', 'status', 'payment_method', 'created_at', 'paid_at'
        ]
        read_only_fields = fields
    
    @extend_schema_field(serializers.IntegerField())
    def get_booking_count(self, obj):
        """Get count of bookings in order"""
        return obj.bookings.count()


class PaymentListSerializer(serializers.ModelSerializer):
    """Serializer for listing payments"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order_number', 'user_email', 'amount', 'currency',
            'payment_method', 'status', 'created_at', 'completed_at'
        ]
        read_only_fields = fields
