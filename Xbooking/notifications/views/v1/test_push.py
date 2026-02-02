"""
Test Push Notification Endpoint
For debugging push notification delivery
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
import logging

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Notifications'],
    summary='Send a test push notification',
    description='Sends a test push notification to verify the push notification system is working',
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_test_push(request):
    """
    Send a test push notification to current user
    """
    try:
        from notifications.services.push_service import PushNotificationService
        from notifications.models_push import PushSubscription
        
        user = request.user
        
        # Check if user has active subscriptions
        subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
        
        if not subscriptions.exists():
            return Response({
                'success': False,
                'error': 'No active push subscriptions found for your account',
                'subscriptions_count': 0
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Format test notification
        notification_data = PushNotificationService.format_notification_data(
            title='Test Push Notification',
            message='This is a test push notification from Xbooking! If you see this, push notifications are working correctly.',
            url='/notifications',
            icon='/xbookinglogonew1.png',
        )
        
        logger.info(f"Sending test push notification to user {user.email}")
        
        # Send push notification
        result = PushNotificationService.send_push_to_user(
            user_id=str(user.id),
            notification_data=notification_data
        )
        
        if result.get('success'):
            return Response({
                'success': True,
                'message': f"Test push notification sent to {result.get('sent', 0)} device(s)",
                'details': {
                    'sent': result.get('sent', 0),
                    'total_subscriptions': result.get('total', 0),
                    'results': result.get('results', [])
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Failed to send push notification'),
                'details': result
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Error sending test push notification: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
