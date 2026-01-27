"""
Withdrawal Serializers V1
"""
from rest_framework import serializers
from bank.models import WithdrawalRequest
from .bank_account import BankAccountSerializer


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal requests"""
    workspace_name = serializers.CharField(source='workspace_wallet.workspace.name', read_only=True)
    bank_account_details = BankAccountSerializer(source='bank_account', read_only=True)
    requested_by_email = serializers.CharField(source='requested_by.email', read_only=True)
    
    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'workspace_wallet', 'workspace_name', 'bank_account',
            'bank_account_details', 'requested_by', 'requested_by_email',
            'amount', 'fee', 'net_amount', 'currency', 'status',
            'reference', 'gateway_reference', 'gateway_response', 'payment_provider',
            'approved_at', 'approved_by', 'processed_at', 'completed_at',
            'failed_at', 'notes', 'admin_notes', 'failure_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'net_amount', 'status', 'reference', 'gateway_reference',
            'gateway_response', 'approved_at', 'approved_by', 'processed_at',
            'completed_at', 'failed_at', 'failure_reason', 'created_at', 'updated_at'
        ]


class CreateWithdrawalRequestSerializer(serializers.Serializer):
    """Serializer for creating withdrawal request"""
    bank_account = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=1000.00,
        help_text='Minimum withdrawal is NGN 1,000'
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        fields = ['bank_account', 'amount', 'notes']


class ProcessWithdrawalSerializer(serializers.Serializer):
    """Serializer for processing withdrawal"""
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        fields = ['admin_notes']


class RequestWithdrawalSerializer(serializers.Serializer):
    bank_account = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1000.00)
    payment_provider = serializers.ChoiceField(choices=[('paystack', 'Paystack'), ('flutterwave', 'Flutterwave')], required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_bank_account(self, value):
        from bank.models import BankAccount
        if not BankAccount.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Bank account not found or inactive.")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
