"""
Serializers for Withdrawal and Bank Account Management
"""
from rest_framework import serializers
from payment.withdrawal_models import BankAccount, Withdrawal, WithdrawalLog


class BankAccountSerializer(serializers.ModelSerializer):
    """Serializer for bank account"""
    
    class Meta:
        model = BankAccount
        fields = [
            'id', 'user', 'workspace', 'account_number', 'account_name', 
            'bank_name', 'bank_code', 'account_type', 'is_default', 
            'is_verified', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'workspace', 'is_verified', 'verified_at', 'created_at', 'updated_at']


class CreateBankAccountSerializer(serializers.ModelSerializer):
    """Serializer for creating bank account"""
    
    class Meta:
        model = BankAccount
        fields = ['account_number', 'account_name', 'bank_name', 'bank_code', 'account_type']


class WithdrawalLogSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal log entries"""
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    
    class Meta:
        model = WithdrawalLog
        fields = ['id', 'status', 'message', 'metadata', 'created_by', 'created_by_email', 'created_at']
        read_only_fields = ['id', 'created_at']


class WithdrawalSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal details"""
    
    requested_by_email = serializers.CharField(source='requested_by.email', read_only=True)
    approved_by_email = serializers.CharField(source='approved_by.email', read_only=True, allow_null=True)
    processed_by_email = serializers.CharField(source='processed_by.email', read_only=True, allow_null=True)
    bank_account_details = BankAccountSerializer(source='bank_account', read_only=True)
    logs = WithdrawalLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Withdrawal
        fields = [
            'id', 'workspace', 'requested_by', 'requested_by_email', 'withdrawal_number',
            'amount', 'currency', 'withdrawal_type', 'description', 'status',
            'bank_account', 'bank_account_details', 'gateway_transaction_id',
            'approved_by', 'approved_by_email', 'approved_at', 'approval_notes',
            'processed_by', 'processed_by_email', 'processed_at',
            'error_message', 'retry_count', 'requested_at', 'updated_at', 'completed_at',
            'logs'
        ]
        read_only_fields = [
            'id', 'workspace', 'requested_by', 'withdrawal_number', 'status',
            'gateway_transaction_id', 'approved_by', 'approved_at', 'processed_by',
            'processed_at', 'error_message', 'retry_count', 'requested_at', 'updated_at',
            'completed_at', 'logs'
        ]


class CreateWithdrawalSerializer(serializers.Serializer):
    """Serializer for creating withdrawal request"""
    
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=100)
    withdrawal_type = serializers.ChoiceField(choices=['revenue', 'commission', 'refund', 'manual'])
    description = serializers.CharField(required=False, allow_blank=True)
    bank_account_id = serializers.UUIDField(required=False, allow_null=True, help_text="If not provided, default account will be used")


class ApproveWithdrawalSerializer(serializers.Serializer):
    """Serializer for approving withdrawal"""
    
    approval_notes = serializers.CharField(required=False, allow_blank=True)


class RejectWithdrawalSerializer(serializers.Serializer):
    """Serializer for rejecting withdrawal"""
    
    reason = serializers.CharField(max_length=500)


class ProcessWithdrawalSerializer(serializers.Serializer):
    """Serializer for processing withdrawal"""
    
    gateway_transaction_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class WithdrawalListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing withdrawals"""
    
    requested_by_email = serializers.CharField(source='requested_by.email', read_only=True)
    bank_account_number = serializers.CharField(source='bank_account.account_number', read_only=True)
    
    class Meta:
        model = Withdrawal
        fields = [
            'id', 'withdrawal_number', 'amount', 'currency', 'withdrawal_type', 'status',
            'requested_by_email', 'bank_account_number', 'requested_at', 'updated_at'
        ]
        read_only_fields = fields
