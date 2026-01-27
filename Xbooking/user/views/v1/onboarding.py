"""
User Onboarding Views V1
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.responses import SuccessResponse, ErrorResponse
from core.services import EventBus, Event, EventTypes
from user.serializers.v1 import OnboardingSerializer, OnboardingStatusSerializer


class OnboardingView(APIView):
    """
    User onboarding management.
    GET: Check onboarding status
    POST: Mark onboarding as completed
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: OnboardingStatusSerializer,
        },
        description='Get onboarding status',
        tags=['User Onboarding']
    )
    def get(self, request):
        """Get onboarding status"""
        serializer = OnboardingStatusSerializer(request.user)
        
        return SuccessResponse(
            message='Onboarding status retrieved',
            data=serializer.data
        )
    
    @extend_schema(
        request=OnboardingSerializer,
        responses={
            200: OpenApiResponse(description='Onboarding completed'),
        },
        description='Mark onboarding as completed',
        tags=['User Onboarding']
    )
    def post(self, request):
        """Complete onboarding"""
        user = request.user
        
        if user.onboarding_completed:
            return SuccessResponse(
                message='Onboarding already completed',
                data={'onboarding_completed': True}
            )
        
        serializer = OnboardingSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Onboarding completion failed',
                errors=serializer.errors,
                status_code=400
            )
        
        user = serializer.save()
        
        # Publish onboarding completed event
        event = Event(
            event_type=EventTypes.EMAIL_SENT,
            data={
                'user_id': str(user.id),
                'notification_type': 'onboarding_completed',
                'title': 'Welcome to Xbooking!',
                'message': 'Your account setup is complete. Start exploring our features.',
                'channels': ['email'],
            },
            source_module='user'
        )
        EventBus.publish(event)
        
        return SuccessResponse(
            message='Onboarding completed successfully',
            data={'onboarding_completed': True}
        )
