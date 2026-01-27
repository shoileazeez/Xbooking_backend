"""
Password Management Views V1
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.responses import SuccessResponse, ErrorResponse
from core.services import EventBus, Event, EventTypes
from user.serializers.v1 import PasswordChangeSerializer, ForcePasswordChangeSerializer


class PasswordChangeView(APIView):
    """
    Password change for authenticated users.
    Requires current password for security.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description='Password changed successfully'),
            400: OpenApiResponse(description='Validation error'),
        },
        description='Change user password (requires current password)',
        tags=['User Profile']
    )
    def post(self, request):
        """Change password"""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Password change failed',
                errors=serializer.errors,
                status_code=400
            )
        
        user = serializer.save()
        
        # Publish password changed event
        event = Event(
            event_type=EventTypes.EMAIL_SENT,
            data={
                'user_id': str(user.id),
                'notification_type': 'password_changed',
                'title': 'Password Changed',
                'message': 'Your password has been changed successfully.',
                'channels': ['email'],
            },
            source_module='user'
        )
        EventBus.publish(event)
        
        return SuccessResponse(
            message='Password changed successfully',
            data={'email': user.email}
        )


class ForcePasswordChangeView(APIView):
    """
    Force password change for workspace-invited users.
    Does NOT require current password (temporary password from invite).
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=ForcePasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description='Password changed successfully'),
            400: OpenApiResponse(description='Validation error'),
        },
        description='Force password change for workspace-invited users',
        tags=['User Profile']
    )
    def post(self, request):
        """Force password change"""
        user = request.user
        
        # Check if force change is required
        if not user.force_password_change:
            return ErrorResponse(
                message='Password change is not required for this account',
                status_code=400
            )
        
        serializer = ForcePasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Password change failed',
                errors=serializer.errors,
                status_code=400
            )
        
        user = serializer.save()
        
        # Publish password changed event
        event = Event(
            event_type=EventTypes.EMAIL_SENT,
            data={
                'user_id': str(user.id),
                'notification_type': 'password_changed',
                'title': 'Password Set Successfully',
                'message': 'Your password has been set. You can now access all features.',
                'channels': ['email'],
            },
            source_module='user'
        )
        EventBus.publish(event)
        
        return SuccessResponse(
            message='Password changed successfully. You can now access all features.',
            data={'email': user.email}
        )
