"""
User Profile Serializer V1
"""
from rest_framework import serializers

from user.models import User, UserRole


class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer.
    Email is read-only, role cannot be changed via profile update.
    """
    workspace_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'avatar_url',
            'role', 'is_business_email', 'business_domain',
            'onboarding_completed', 'force_password_change',
            'is_active', 'created_at', 'updated_at', 'workspace_count'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'is_business_email', 'business_domain',
            'force_password_change', 'is_active', 'created_at', 'updated_at'
        ]
    
    def get_workspace_count(self, obj):
        """Get count of workspaces user belongs to"""
        try:
            from workspace.models import WorkspaceUser
            return WorkspaceUser.objects.filter(user=obj, is_active=True).count()
        except Exception:
            return 0
    
    def update(self, instance, validated_data):
        """Update user profile with service layer"""
        from user.services.user_service import UserService
        
        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Publish event
        request = self.context.get('request')
        updated_by = request.user if request else instance
        UserService.update_user(instance, updated_by=updated_by)
        
        return instance


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested representations"""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'avatar_url', 'role']
        read_only_fields = fields
