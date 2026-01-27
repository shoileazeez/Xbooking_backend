"""
Notification Preference ViewSet V1
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.views import CachedModelViewSet
from core.throttling import UserRateThrottle
from notifications.models import NotificationPreference
from notifications.serializers.v1 import (
    NotificationPreferenceSerializer,
    UpdatePreferenceSerializer
)


class NotificationPreferenceViewSet(CachedModelViewSet):
    """
    ViewSet for managing user notification preferences
    
    Endpoints:
    - GET /preferences/ - Get current user's notification preferences
    - PATCH /preferences/update/ - Update notification preferences
    """
    
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    cache_timeout = 300  # 5 minutes cache
    
    def get_queryset(self):
        """Return notification preferences for current user only"""
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        """Get or create notification preferences for current user"""
        preference, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = self.get_serializer(preference)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'])
    def update_preferences(self, request):
        """
        Update notification preferences
        
        PATCH /api/v1/notifications/preferences/update_preferences/
        """
        preference, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        serializer = UpdatePreferenceSerializer(
            preference, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Invalidate cache
        self.invalidate_cache(preference)
        
        return Response({
            'message': 'Notification preferences updated',
            'preferences': NotificationPreferenceSerializer(preference).data
        })
