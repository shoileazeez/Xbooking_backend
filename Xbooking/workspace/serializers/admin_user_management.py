"""
Serializers for Admin User Management
"""
from rest_framework import serializers
from user.models import User


class AdminResetPasswordSerializer(serializers.Serializer):
    """Serializer for admin password reset"""
    send_email = serializers.BooleanField(default=True, required=False)
    
    class Meta:
        fields = ['send_email']


class AdminForcePasswordChangeSerializer(serializers.Serializer):
    """Serializer for forcing password change"""
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    class Meta:
        fields = ['reason']


class AdminRevokeAccessSerializer(serializers.Serializer):
    """Serializer for revoking user access"""
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['reason']


class AdminRestoreAccessSerializer(serializers.Serializer):
    """Serializer for restoring user access"""
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['reason']


class AdminDeleteAccountSerializer(serializers.Serializer):
    """Serializer for deleting user account"""
    confirm = serializers.BooleanField(required=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['confirm', 'reason']
    
    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("You must confirm the deletion.")
        return value


class AdminUserStatusResponseSerializer(serializers.Serializer):
    """Response serializer for user status operations"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    user_id = serializers.CharField()
    email = serializers.CharField()
    status = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True)
