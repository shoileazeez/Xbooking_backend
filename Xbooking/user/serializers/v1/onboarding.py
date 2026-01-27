"""
User Onboarding Serializer V1
"""
from rest_framework import serializers

from user.models import User


class OnboardingSerializer(serializers.Serializer):
    """
    Onboarding completion serializer.
    Marks user as having completed onboarding flow.
    """
    onboarding_completed = serializers.BooleanField(default=True)
    
    def save(self):
        """Mark onboarding as completed"""
        from user.services.user_service import UserService
        
        user = self.context['request'].user
        user.onboarding_completed = True
        user.save()
        
        # Publish event
        UserService.update_user(user, updated_by=user)
        
        return user


class OnboardingStatusSerializer(serializers.ModelSerializer):
    """Serializer to check onboarding status"""
    
    class Meta:
        model = User
        fields = ['onboarding_completed', 'force_password_change']
        read_only_fields = fields
