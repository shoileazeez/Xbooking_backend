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
        
        logger.info(f"=== Test Push Request from user: {user.email} ===")
        
        # Check if user has active subscriptions
        subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
        sub_count = subscriptions.count()
        
        logger.info(f"Found {sub_count} active subscription(s) for user")
        
        if not subscriptions.exists():
            logger.warning(f"No active subscriptions found for user {user.email}")
            # Also check for inactive subscriptions
            inactive_count = PushSubscription.objects.filter(user=user, is_active=False).count()
            logger.info(f"User has {inactive_count} inactive subscription(s)")
            
            return Response({
                'success': False,
                'error': 'No active push subscriptions found for your account',
                'subscriptions_count': 0,
                'inactive_subscriptions': inactive_count
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Log subscription details
        for idx, sub in enumerate(subscriptions, 1):
            logger.info(f"Subscription {idx}: ID={sub.id}, Endpoint={sub.endpoint[:80]}..., LastUsed={sub.last_used_at}")
        
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
