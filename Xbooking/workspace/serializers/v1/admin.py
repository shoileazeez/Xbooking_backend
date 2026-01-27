"""
Admin User Management Serializers for v1 API
"""
from rest_framework import serializers
from workspace.models import WorkspaceUser


class AdminResetPasswordSerializer(serializers.Serializer):
    """Serializer for admin password reset"""
    send_email = serializers.BooleanField(default=True, required=False)


class AdminUserActionSerializer(serializers.Serializer):
    """Serializer for admin user actions"""
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer for admin"""
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = WorkspaceUser
        fields = [
            'id', 'workspace_name', 'user_id', 'user_name', 'user_email',
            'user_phone', 'role', 'is_active', 'joined_at', 'created_at'
        ]
        read_only_fields = ['id', 'joined_at', 'created_at']
