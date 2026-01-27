"""
Payment V1 Serializers - Refund Management
"""
from rest_framework import serializers
from payment.models import Refund
from decimal import Decimal


class RefundSerializer(serializers.ModelSerializer):
    """Detailed refund serializer"""
    payment_id = serializers.UUIDField(source='payment.id', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    payment_amount = serializers.DecimalField(
        source='payment.amount',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'payment_id', 'payment_amount',
            'order', 'order_number', 'workspace', 'workspace_name',
            'user', 'user_email', 'amount', 'reason',
            'reason_description', 'gateway_refund_id', 'status',
            'requested_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'gateway_refund_id', 'status',
            'requested_at', 'completed_at'
        ]


class RefundListSerializer(serializers.ModelSerializer):
    """Optimized serializer for refund lists"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'order', 'order_number', 'workspace', 'workspace_name',
            'amount', 'reason', 'status', 'requested_at', 'completed_at'
        ]
        read_only_fields = fields


class CreateRefundSerializer(serializers.Serializer):
    """Serializer for requesting refunds"""
    payment_id = serializers.UUIDField(
        help_text="Payment ID to refund"
    )
    reason = serializers.ChoiceField(
        choices=['user_request', 'booking_cancelled', 'system_error', 'duplicate_charge', 'other'],
        help_text="Reason for refund"
    )
    reason_description = serializers.CharField(
        max_length=1000,
        help_text="Detailed description of refund reason"
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Refund amount (defaults to full payment amount)"
    )
    
    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value and value <= Decimal('0'):
            raise serializers.ValidationError("Refund amount must be positive")
        return value


__all__ = [
    'RefundSerializer',
    'RefundListSerializer',
    'CreateRefundSerializer',
]
