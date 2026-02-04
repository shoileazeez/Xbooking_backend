"""
Push Notification Views
Handles web push notification subscription and delivery
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Notifications'],
    summary='Subscribe to push notifications',
    description='Subscribe to web push notifications by providing the push subscription details',
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def push_subscribe(request):
    """
    Subscribe to push notifications
    
    Request body:
    {
        "endpoint": "https://...",
        "keys": {
            "p256dh": "...",
            "auth": "..."
        }
    }
    """
    try:
        from notifications.models_push import PushSubscription
        
        logger.info(f"=== Push Subscribe Request from user: {request.user.email} ===")
        logger.info(f"Request data keys: {request.data.keys()}")
        
        endpoint = request.data.get('endpoint')
        keys = request.data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')
        
        logger.info(f"Endpoint: {endpoint[:80] if endpoint else 'None'}...")
        logger.info(f"P256dh key length: {len(p256dh) if p256dh else 0}")
        logger.info(f"Auth key length: {len(auth) if auth else 0}")
        
        if not all([endpoint, p256dh, auth]):
            logger.error("Missing required fields")
            return Response({
                'success': False,
                'error': 'Missing required fields: endpoint, keys.p256dh, keys.auth'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user agent for tracking
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        logger.info(f"Checking for existing subscriptions with this endpoint...")
        # First, deactivate any existing subscriptions for this endpoint from other users
        # (in case device changed hands or user logged out/in)
        other_user_subs = PushSubscription.objects.filter(
            endpoint=endpoint
        ).exclude(
            user=request.user
        )
        if other_user_subs.exists():
            logger.info(f"Found {other_user_subs.count()} subscriptions from other users, deactivating...")
            other_user_subs.update(is_active=False)
        
        logger.info(f"Creating or updating subscription for user {request.user.email}...")
        # Create or update subscription for current user
        subscription, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh_key': p256dh,
                'auth_key': auth,
                'user_agent': user_agent,
                'is_active': True,
                'last_used_at': timezone.now()
            }
        )
        
        logger.info(f"Subscription {'created' if created else 'updated'} with ID: {subscription.id}")
        
        # Ensure user field is set even if record existed
        if subscription.user != request.user:
            logger.info(f"Updating user field from {subscription.user.email} to {request.user.email}")
            subscription.user = request.user
            subscription.is_active = True
            subscription.save()
        
        # Count total active subscriptions for this user
        total_subs = PushSubscription.objects.filter(user=request.user, is_active=True).count()
        logger.info(f"User now has {total_subs} active subscription(s)")
        logger.info(f"Push subscription {'created' if created else 'updated'} for user {request.user.email}")
        
        return Response({
            'success': True,
            'message': 'Successfully subscribed to push notifications',
            'subscription_id': subscription.id,
            'total_active_subscriptions': total_subs,
            'created': created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error subscribing to push notifications: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Notifications'],
    summary='Unsubscribe from push notifications',
    description='Unsubscribe from web push notifications by providing the endpoint',
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def push_unsubscribe(request):
    """
    Unsubscribe from push notifications
    
    Request body:
    {
        "endpoint": "https://..."
    }
    """
    try:
        from notifications.models_push import PushSubscription
        
        endpoint = request.data.get('endpoint')
        
        if not endpoint:
            return Response({
                'success': False,
                'error': 'Missing required field: endpoint'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find and deactivate/delete subscription
        deleted_count = PushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint
        ).delete()[0]
        
        if deleted_count > 0:
            logger.info(f"Push subscription removed for user {request.user.email}")
            return Response({
                'success': True,
                'message': 'Successfully unsubscribed from push notifications'
            })
        else:
            return Response({
                'success': False,
                'message': 'Subscription not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error unsubscribing from push notifications: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Notifications'],
    summary='Get user\'s push subscriptions',
    description='Get all active push subscriptions for the current user',
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_push_subscriptions(request):
    """
    Get all active push subscriptions for current user
    """
    try:
        from notifications.models_push import PushSubscription
        
        subscriptions = PushSubscription.objects.filter(
            user=request.user,
            is_active=True
        ).values('id', 'endpoint', 'user_agent', 'created_at', 'last_used_at')
        
        return Response({
            'success': True,
            'count': len(subscriptions),
            'subscriptions': list(subscriptions)
        })
        
    except Exception as e:
        logger.error(f"Error fetching push subscriptions: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Notifications'],
    summary='Check if user has active subscriptions',
    description='Quick check if user has any active push subscriptions',
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_subscription_status(request):
    """
    Check if user has active push subscriptions
    """
    try:
        from notifications.models_push import PushSubscription
        
        has_subscription = PushSubscription.objects.filter(
            user=request.user,
            is_active=True
        ).exists()
        
        count = PushSubscription.objects.filter(
            user=request.user,
            is_active=True
        ).count()
        
        return Response({
            'success': True,
            'has_subscription': has_subscription,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Error checking subscription status: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
