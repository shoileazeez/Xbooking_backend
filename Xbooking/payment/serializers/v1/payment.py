"""
Payment V1 Serializers - Payment Processing
"""
from rest_framework import serializers
from payment.models import Payment
from decimal import Decimal


class PaymentSerializer(serializers.ModelSerializer):
    """Detailed payment serializer"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'workspace', 'workspace_name',
            'user', 'user_email', 'amount', 'currency',
            'payment_method', 'gateway_transaction_id',
            'status', 'gateway_response', 'retry_count',
            'last_retry_at', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'gateway_transaction_id', 'gateway_response',
            'retry_count', 'last_retry_at', 'created_at',
            'updated_at', 'completed_at'
        ]


class PaymentListSerializer(serializers.ModelSerializer):
    """Optimized serializer for payment lists"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'workspace', 'workspace_name',
            'amount', 'currency', 'payment_method', 'status',
            'created_at', 'completed_at'
        ]
        read_only_fields = fields


class InitiatePaymentSerializer(serializers.Serializer):
    """Serializer for initiating payments"""
    order_id = serializers.UUIDField(
        help_text="Order ID to process payment for"
    )
    payment_method = serializers.ChoiceField(
        choices=['paystack', 'flutterwave', 'stripe', 'wallet'],
        help_text="Payment gateway to use"
    )
    callback_url = serializers.URLField(
        required=False,
        help_text="Optional callback URL for payment completion"
    )


class PaymentCallbackSerializer(serializers.Serializer):
    """Serializer for payment callback/verification"""
    reference = serializers.CharField(
        help_text="Payment reference from gateway"
    )
    status = serializers.CharField(
        required=False,
        help_text="Payment status from gateway"
    )


class PaymentStatusSerializer(serializers.ModelSerializer):
    """Serializer for payment status checks"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    order_total = serializers.DecimalField(
        source='order.total_amount',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'order_total',
            'amount', 'currency', 'payment_method',
            'gateway_transaction_id', 'status',
            'created_at', 'completed_at'
        ]
        read_only_fields = fields


__all__ = [
    'PaymentSerializer',
    'PaymentListSerializer',
    'InitiatePaymentSerializer',
    'PaymentCallbackSerializer',
    'PaymentStatusSerializer',
]
