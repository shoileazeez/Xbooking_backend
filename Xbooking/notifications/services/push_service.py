"""
Push Notification Service
Handles sending web push notifications to subscribed users
"""
import json
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Check if pywebpush is available
try:
    from pywebpush import webpush, WebPushException
    WEBPUSH_AVAILABLE = True
except ImportError:
    logger.warning("pywebpush not installed. Push notifications will not work. Install with: pip install pywebpush")
    WEBPUSH_AVAILABLE = False


class PushNotificationService:
    """
    Service for sending web push notifications
    """
    
    @staticmethod
    def send_push_to_user(user_id: str, notification_data: Dict) -> Dict[str, any]:
        """
        Send push notification to all active subscriptions for a user
        
        Args:
            user_id: User ID to send notification to
            notification_data: Notification data to send
            
        Returns:
            Dict with success status and results
        """
        if not WEBPUSH_AVAILABLE:
            logger.warning("pywebpush not available, skipping push notification")
            return {'success': False, 'error': 'pywebpush not installed'}
        
        try:
            from notifications.models_push import PushSubscription
            from user.models import User
            
            user = User.objects.get(id=user_id)
            subscriptions = PushSubscription.objects.filter(
                user=user,
                is_active=True
            )
            
            if not subscriptions.exists():
                logger.info(f"No active push subscriptions for user {user.email}")
                return {'success': True, 'message': 'No active subscriptions', 'sent': 0}
            
            # Get VAPID keys from settings
            vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', None)
            vapid_admin_email = getattr(settings, 'VAPID_ADMIN_EMAIL', 'admin@xbooking.dev')
            
            if not vapid_private_key:
                logger.error("VAPID_PRIVATE_KEY not set in settings")
                return {'success': False, 'error': 'VAPID keys not configured'}
            
            results = []
            sent_count = 0
            
            for subscription in subscriptions:
                try:
                    # Send push notification
                    response = webpush(
                        subscription_info=subscription.to_dict(),
                        data=json.dumps(notification_data),
                        vapid_private_key=vapid_private_key,
                        vapid_claims={
                            "sub": f"mailto:{vapid_admin_email}"
                        }
                    )
                    
                    # Update last used timestamp
                    subscription.last_used_at = timezone.now()
                    subscription.save(update_fields=['last_used_at'])
                    
                    sent_count += 1
                    results.append({
                        'subscription_id': subscription.id,
                        'success': True,
                        'status_code': response.status_code
                    })
                    
                    logger.info(f"Push notification sent to subscription {subscription.id}")
                    
                except WebPushException as e:
                    logger.error(f"WebPush error for subscription {subscription.id}: {str(e)}")
                    
                    status_code = None
                    try:
                        status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
                    except:
                        pass
                    
                    # If subscription is expired/invalid (410), mark as inactive
                    if status_code == 410 or '410' in str(e) or 'expired' in str(e).lower() or 'unsubscribed' in str(e).lower():
                        subscription.is_active = False
                        subscription.save(update_fields=['is_active'])
                        logger.warning(f"Marked subscription {subscription.id} as inactive (expired/unsubscribed)")
                    
                    results.append({
                        'subscription_id': subscription.id,
                        'success': False,
                        'error': str(e),
                        'status_code': status_code
                    })
                    
                except Exception as e:
                    logger.error(f"Error sending push to subscription {subscription.id}: {str(e)}")
                    results.append({
                        'subscription_id': subscription.id,
                        'success': False,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'sent': sent_count,
                'total': len(subscriptions),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def format_notification_data(
        title: str,
        message: str,
        notification_id: Optional[str] = None,
        url: Optional[str] = None,
        icon: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Format notification data for push delivery
        
        Args:
            title: Notification title
            message: Notification message
            notification_id: Optional notification ID
            url: Optional URL to open on click
            icon: Optional icon URL
            **kwargs: Additional data
            
        Returns:
            Formatted notification data dict
        """
        return {
            'title': title,
            'body': message,
            'message': message,  # Backwards compatibility
            'icon': icon or '/xbookinglogonew1.png',
            'badge': '/xbookinglogonew1.png',
            'tag': f'notification-{notification_id}' if notification_id else 'xbooking-notification',
            'url': url or '/notifications',
            'notification_id': notification_id,
            'data': kwargs,
            'requireInteraction': False,
        }
