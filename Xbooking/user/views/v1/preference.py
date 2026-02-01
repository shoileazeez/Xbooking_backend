"""
User Preference ViewSet V1
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.models import UserPreference
from user.serializers.v1 import UserPreferenceSerializer, UpdateUserPreferenceSerializer


class UserPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user preferences
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserPreferenceSerializer
    
    def get_queryset(self):
        """Return only the current user's preference"""
        return UserPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create the user's preference"""
        preference, created = UserPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference
    
    def list(self, request):
        """Get current user's preferences"""
        preference = self.get_object()
        serializer = UserPreferenceSerializer(preference)
        return Response({
            'success': True,
            'message': 'Preferences retrieved successfully',
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        """Update user preferences - allow PUT on list endpoint"""
        # If no pk is provided, treat it as updating the user's preference
        if 'pk' not in kwargs or kwargs['pk'] is None:
            instance = self.get_object()
            serializer = UpdateUserPreferenceSerializer(
                instance,
                data=request.data,
                partial=True
            )
            
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Preferences updated successfully',
                    'data': UserPreferenceSerializer(instance).data
                })
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Otherwise, use the default ModelViewSet behavior
        return super().update(request, *args, **kwargs)
    
    def create(self, request):
        """Create or update user preferences"""
        instance = self.get_object()
        serializer = UpdateUserPreferenceSerializer(
            instance,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Preferences updated successfully',
                'data': UserPreferenceSerializer(instance).data
            })
        
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['put'])
    def update_preferences(self, request):
        """Update user preferences via PUT on list endpoint"""
        instance = self.get_object()
        serializer = UpdateUserPreferenceSerializer(
            instance,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Preferences updated successfully',
                'data': UserPreferenceSerializer(instance).data
            })
        
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
