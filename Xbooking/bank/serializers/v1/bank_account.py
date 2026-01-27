"""
Bank Account Serializers V1
"""
from rest_framework import serializers
from bank.models import BankAccount


class BankAccountSerializer(serializers.ModelSerializer):
    """Serializer for bank accounts"""
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BankAccount
        fields = [
            'id', 'user', 'workspace', 'owner_name', 'account_number',
            'account_name', 'bank_name', 'bank_code', 'account_type',
            'is_verified', 'verified_at', 'is_default', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'verified_at', 'created_at', 'updated_at'
        ]
    
    def get_owner_name(self, obj):
        if obj.user:
            return obj.user.email
        elif obj.workspace:
            return obj.workspace.name
        return None


class CreateBankAccountSerializer(serializers.Serializer):
    """Serializer for creating bank account"""
    account_number = serializers.CharField(max_length=20)
    account_name = serializers.CharField(max_length=200)
    bank_name = serializers.CharField(max_length=100)
    bank_code = serializers.CharField(max_length=10)
    account_type = serializers.ChoiceField(
        choices=['savings', 'current'],
        default='savings'
    )
    is_default = serializers.BooleanField(default=False)
    
    class Meta:
        fields = [
            'account_number', 'account_name', 'bank_name', 
            'bank_code', 'account_type', 'is_default'
        ]
