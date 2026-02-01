"""
Notification signals
Automatically trigger push notifications when notifications are created
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.models import Notification
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Notification)
def send_push_notification_on_create(sender, instance, created, **kwargs):
    """
    Automatically send push notifications when a notification is created
    For in-app notifications, also send push notification to user's devices
    """
    if not created:
        return  # Only process new notifications
    
    # Send push notifications for in-app notifications
    if instance.channel == 'in_app':
        try:
            from notifications.services.push_service import PushNotificationService
            from notifications.models import NotificationPreference
            
            # Check if user has push notifications enabled
            try:
                preferences = NotificationPreference.objects.get(user=instance.user)
                if not preferences.push_notifications:
                    logger.info(f"Push notifications disabled for user {instance.user.email}")
                    return
            except NotificationPreference.DoesNotExist:
                # If no preferences exist, default to sending
                pass
            
            # Format notification data for push
            notification_data = PushNotificationService.format_notification_data(
                title=instance.title,
                message=instance.message,
                notification_id=str(instance.id),
                url=instance.data.get('url', '/notifications') if instance.data else '/notifications',
                icon='/xbookinglogonew1.png',
                notification_type=instance.notification_type,
                **(instance.data if instance.data else {})
            )
            
            # Send push notification immediately (not via Celery for real-time delivery)
            result = PushNotificationService.send_push_to_user(
                user_id=str(instance.user.id),
                notification_data=notification_data
            )
            
            if result.get('success') and result.get('sent', 0) > 0:
                logger.info(f"Push notification sent for {instance.user.email}: {instance.title} ({result.get('sent')} devices)")
            else:
                logger.warning(f"Push notification not sent: {result.get('message', result.get('error', 'Unknown error'))}")
                
        except Exception as e:
            logger.error(f"Failed to send push notification: {str(e)}", exc_info=True)

