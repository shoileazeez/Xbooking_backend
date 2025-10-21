"""
Serializers for User Password Change
"""
from rest_framework import serializers
from user.models import User


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        fields = ['current_password', 'new_password']


class ForcedPasswordChangeSerializer(serializers.Serializer):
    """Serializer for forced password change after admin reset"""
    new_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        fields = ['new_password']


class CheckPasswordChangeRequiredSerializer(serializers.Serializer):
    """Response serializer for checking if password change is required"""
    force_password_change = serializers.BooleanField()
    message = serializers.CharField(required=False)
    reason = serializers.CharField(required=False)
    
    class Meta:
        fields = ['force_password_change', 'message', 'reason']


class PasswordChangeResponseSerializer(serializers.Serializer):
    """Response serializer for password change operations"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    force_password_change = serializers.BooleanField()
    
    class Meta:
        fields = ['success', 'message', 'force_password_change']
