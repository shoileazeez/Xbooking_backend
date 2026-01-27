"""
Password Management Serializers V1
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


class PasswordChangeSerializer(serializers.Serializer):
    """
    Password change serializer for authenticated users.
    Requires current password for security.
    """
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    def validate_current_password(self, value):
        """Validate current password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value
    
    def validate(self, attrs):
        """Validate new password"""
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        # Check passwords match
        if new_password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        
        # Validate password strength
        try:
            validate_password(new_password, user=self.context['request'].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })
        
        return attrs
    
    def save(self):
        """Change user password"""
        from user.services.user_service import UserService
        
        user = self.context['request'].user
        new_password = self.validated_data['new_password']
        
        user.set_password(new_password)
        user.force_password_change = False  # Clear force change flag
        user.save()
        
        # Publish event
        UserService.update_user(user, updated_by=user)
        
        return user


class ForcePasswordChangeSerializer(serializers.Serializer):
    """
    Force password change serializer for workspace-invited users.
    Does NOT require current password (they have temporary one).
    """
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        """Validate new password"""
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        user = self.context['request'].user
        
        # Check if force_password_change is required
        if not user.force_password_change:
            raise serializers.ValidationError(
                'Password change is not required for this account.'
            )
        
        # Check passwords match
        if new_password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        
        # Validate password strength
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })
        
        return attrs
    
    def save(self):
        """Update password and clear force change flag"""
        from user.services.user_service import UserService
        
        user = self.context['request'].user
        new_password = self.validated_data['new_password']
        
        user.set_password(new_password)
        user.force_password_change = False
        user.save()
        
        # Publish event
        UserService.update_user(user, updated_by=user)
        
        return user
