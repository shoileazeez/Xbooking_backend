"""
User Preference ViewSet V1
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.models import UserPreference
from user.serializers.v1 import UserPreferenceSerializer, UpdateUserPreferenceSerializer


class UserPreferenceViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user preferences
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get current user's preferences"""
        preference, created = UserPreference.objects.get_or_create(
            user=request.user
        )
        serializer = UserPreferenceSerializer(preference)
        return Response({
            'success': True,
            'message': 'Preferences retrieved successfully',
            'data': serializer.data
        })
    
    def update(self, request, pk=None):
        """Update user preferences"""
        preference, created = UserPreference.objects.get_or_create(
            user=request.user
        )
        
        serializer = UpdateUserPreferenceSerializer(
            preference,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Preferences updated successfully',
                'data': UserPreferenceSerializer(preference).data
            })
        
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def reset(self, request):
        """Reset preferences to default"""
        try:
            preference = UserPreference.objects.get(user=request.user)
            preference.delete()
            # Will be recreated with defaults on next access
            return Response({
                'success': True,
                'message': 'Preferences reset to default successfully'
            })
        except UserPreference.DoesNotExist:
            return Response({
                'success': True,
                'message': 'No preferences to reset'
            })
