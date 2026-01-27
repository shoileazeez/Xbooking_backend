"""
Wallet Serializers V1
"""
from rest_framework import serializers
from bank.models import Wallet, WorkspaceWallet, Transaction, Deposit
from drf_spectacular.utils import extend_schema_field
from decimal import Decimal

class WalletSerializer(serializers.ModelSerializer):
    """Serializer for user wallet"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'user', 'user_email', 'user_name', 'balance', 
            'currency', 'is_active', 'is_locked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'balance', 'created_at', 'updated_at']
    
    @extend_schema_field(serializers.CharField())
    def get_user_name(self, obj):
        return obj.user.full_name or obj.user.email


class WorkspaceWalletSerializer(serializers.ModelSerializer):
    """Serializer for workspace wallet"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = WorkspaceWallet
        fields = [
            'id', 'workspace', 'workspace_name', 'balance', 'total_earnings',
            'total_withdrawn', 'currency', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'workspace', 'balance', 'total_earnings', 
            'total_withdrawn', 'created_at', 'updated_at'
        ]


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions"""
    wallet_owner = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'reference', 'transaction_type', 'category', 'amount', 
            'currency', 'wallet', 'workspace_wallet', 'wallet_owner',
            'booking', 'order', 'balance_before', 'balance_after',
            'status', 'description', 'metadata', 'processed_at',
            'failed_at', 'failure_reason', 'created_at'
        ]
        read_only_fields = fields
    
    @extend_schema_field(serializers.CharField())
    def get_wallet_owner(self, obj):
        if obj.wallet:
            return obj.wallet.user.email
        elif obj.workspace_wallet:
            return obj.workspace_wallet.workspace.name
        return None


class DepositSerializer(serializers.ModelSerializer):
    """Serializer for deposits"""
    wallet_balance = serializers.DecimalField(
        source='wallet.balance', 
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = Deposit
        fields = [
            'id', 'wallet', 'wallet_balance', 'amount', 'currency',
            'payment_method', 'reference', 'gateway_reference',
            'status', 'completed_at', 'failed_at', 'notes',
            'failure_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'wallet', 'reference', 'gateway_reference',
            'status', 'completed_at', 'failed_at', 'created_at', 'updated_at'
        ]
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        for k, v in data.items():
            if isinstance(v, Decimal):
                data[k] = float(v)
        return data

class InitiateDepositSerializer(serializers.Serializer):
    """Serializer for initiating deposit"""
    amount = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2,
        min_value=100.00,
        help_text='Minimum deposit is NGN 100'
    )
    payment_method = serializers.ChoiceField(
        choices=['card', 'bank_transfer', 'paystack', 'flutterwave'],
        default='paystack'
    )
    
    class Meta:
        fields = ['amount', 'payment_method']
