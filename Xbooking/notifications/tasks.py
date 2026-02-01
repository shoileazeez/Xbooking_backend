"""
Celery tasks for notifications
"""
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from notifications.models import Notification, NotificationPreference, BroadcastNotification, NotificationLog
from workspace.models import WorkspaceUser
from Xbooking.mailjet_utils import send_mailjet_email

@shared_task(bind=True, max_retries=3)
def send_notification(self, notification_id):
    """
    Send a notification via specified channel (idempotent - safe to retry)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.user
        
        # Idempotency check - if already sent, skip
        if notification.is_sent:
            logger.info(f"Notification {notification_id} already sent, skipping")
            return {'success': True, 'message': 'Notification already sent', 'duplicate_prevented': True}
        
        # Check user preferences
        if hasattr(user, 'notification_preferences'):
            preferences = user.notification_preferences
            
            # Channel-specific checks
            if notification.channel == 'email' and not preferences.email_enabled:
                return {'success': True, 'message': 'Email notifications disabled for user'}
            elif notification.channel == 'sms' and not preferences.sms_enabled:
                return {'success': True, 'message': 'SMS notifications disabled for user'}
            elif notification.channel == 'push' and not preferences.push_enabled:
                return {'success': True, 'message': 'Push notifications disabled for user'}
            elif notification.channel == 'in_app' and not preferences.in_app_enabled:
                return {'success': True, 'message': 'In-app notifications disabled for user'}
        
        # Send based on channel
        if notification.channel == 'email':
            return _send_email_notification(notification)
        elif notification.channel == 'sms':
            return _send_sms_notification(notification)
        elif notification.channel == 'push':
            return _send_push_notification(notification)
        elif notification.channel == 'in_app':
            return _send_in_app_notification(notification)
        
        return {'success': False, 'error': 'Unknown channel'}
    except Notification.DoesNotExist:
        logger.warning(f"Notification {notification_id} not found - may have been deleted")
        return {'success': False, 'error': f'Notification {notification_id} not found'}
    except Exception as e:
        logger.error(f"Error sending notification {notification_id}: {str(e)}")
        return {'success': False, 'error': str(e)}


def _send_email_notification(notification):
    """Send email notification"""
    try:
        user = notification.user
        
        # Prepare email content
        context = {
            'user_name': user.full_name or user.email,
            'title': notification.title,
            'message': notification.message,
            'data': notification.data,
        }
        
        # Render template
        html_content = render_to_string('emails/generic_notification.html', context)
        text_content = render_to_string('emails/generic_notification.txt', context)
        
        # Send email via Mailjet API
        result = send_mailjet_email(
            subject=notification.title,
            to_email=user.email,
            to_name=user.full_name or user.email,
            html_content=html_content,
            text_content=text_content
        )
        
        if not result.get('success'):
            raise Exception(f"Failed to send email: {result.get('error')}")
        
        # Update notification status
        notification.is_sent = True
        notification.sent_at = timezone.now()
        notification.save()
        
        # Log delivery
        NotificationLog.objects.create(
            notification=notification,
            status='sent',
            delivered_at=timezone.now()
        )
        
        return {'success': True, 'message': 'Email sent successfully'}
    except Exception as e:
        # Log failure
        NotificationLog.objects.create(
            notification=notification,
            status='failed',
            error_message=str(e)
        )
        return {'success': False, 'error': str(e)}


def _send_sms_notification(notification):
    """Send SMS notification (stub for SMS gateway integration)"""
    try:
        user = notification.user
        
        # SMS gateway integration would go here
        # For now, just mark as sent
        notification.is_sent = True
        notification.sent_at = timezone.now()
        notification.save()
        
        NotificationLog.objects.create(
            notification=notification,
            status='sent',
            delivered_at=timezone.now()
        )
        
        return {'success': True, 'message': 'SMS sent successfully'}
    except Exception as e:
        NotificationLog.objects.create(
            notification=notification,
            status='failed',
            error_message=str(e)
        )
        return {'success': False, 'error': str(e)}


def _send_push_notification(notification):
    """Send web push notification to user's subscribed devices"""
    try:
        from notifications.services.push_service import PushNotificationService
        
        user = notification.user
        
        # Format notification data for push
        notification_data = PushNotificationService.format_notification_data(
            title=notification.title,
            message=notification.message,
            notification_id=str(notification.id),
            url=notification.data.get('url', '/notifications') if notification.data else '/notifications',
            icon='/xbookinglogonew1.png',
            notification_type=notification.notification_type,
            **notification.data if notification.data else {}
        )
        
        # Send push notification
        result = PushNotificationService.send_push_to_user(
            user_id=str(user.id),
            notification_data=notification_data
        )
        
        if result.get('success') and result.get('sent', 0) > 0:
            # Mark as sent if at least one push was delivered
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save()
            
            NotificationLog.objects.create(
                notification=notification,
                status='sent',
                delivered_at=timezone.now(),
                metadata={'push_results': result}
            )
            
            return {'success': True, 'message': f'Push sent to {result.get("sent")} device(s)'}
        else:
            # No active subscriptions or all failed
            NotificationLog.objects.create(
                notification=notification,
                status='failed',
                error_message=result.get('error', 'No active subscriptions')
            )
            return {'success': False, 'error': result.get('error', 'No active subscriptions')}
            
    except Exception as e:
        NotificationLog.objects.create(
            notification=notification,
            status='failed',
            error_message=str(e)
        )
        return {'success': False, 'error': str(e)}


def _send_in_app_notification(notification):
    """Send in-app notification (stored in DB only)"""
    try:
        notification.is_sent = True
        notification.sent_at = timezone.now()
        notification.save()
        
        NotificationLog.objects.create(
            notification=notification,
            status='sent',
            delivered_at=timezone.now()
        )
        
        return {'success': True, 'message': 'In-app notification sent successfully'}
    except Exception as e:
        NotificationLog.objects.create(
            notification=notification,
            status='failed',
            error_message=str(e)
        )
        return {'success': False, 'error': str(e)}


@shared_task
def send_broadcast_notification(broadcast_id):
    """
    Send broadcast notification to target users
    """
    try:
        broadcast = BroadcastNotification.objects.get(id=broadcast_id)
        workspace = broadcast.workspace
        
        # Determine target users
        if broadcast.target_users.exists():
            target_users = broadcast.target_users.all()
        else:
            # Get workspace users with target roles
            workspace_users = WorkspaceUser.objects.filter(
                workspace=workspace,
                role__in=broadcast.target_roles if broadcast.target_roles else ['admin', 'manager', 'staff', 'user']
            )
            target_users = [wu.user for wu in workspace_users]
        
        total = len(target_users)
        sent_count = 0
        failed_count = 0
        
        # Create notifications for each user
        for user in target_users:
            try:
                for channel in broadcast.channels:
                    notification = Notification.objects.create(
                        user=user,
                        notification_type='system_alert',
                        channel=channel,
                        title=broadcast.title,
                        message=broadcast.message,
                        data={'broadcast_id': str(broadcast.id)}
                    )
                    
                    # Send notification
                    result = send_notification.delay(str(notification.id))
                    
                    if result:
                        sent_count += 1
                    else:
                        failed_count += 1
            except Exception as e:
                failed_count += 1
                continue
        
        # Update broadcast stats
        broadcast.total_recipients = total
        broadcast.sent_count = sent_count
        broadcast.failed_count = failed_count
        broadcast.save()
        
        return {
            'success': True,
            'total': total,
            'sent': sent_count,
            'failed': failed_count,
            'message': f'Broadcast sent to {sent_count}/{total} users'
        }
    except BroadcastNotification.DoesNotExist:
        return {'success': False, 'error': f'Broadcast {broadcast_id} not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
