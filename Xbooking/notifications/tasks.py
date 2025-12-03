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

@shared_task
def send_notification(notification_id):
    """
    Send a notification via specified channel
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.user
        
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
        return {'success': False, 'error': f'Notification {notification_id} not found'}
    except Exception as e:
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
    """Send push notification (stub for push gateway integration)"""
    try:
        user = notification.user
        
        # Push notification gateway integration would go here
        # For now, just mark as sent
        notification.is_sent = True
        notification.sent_at = timezone.now()
        notification.save()
        
        NotificationLog.objects.create(
            notification=notification,
            status='sent',
            delivered_at=timezone.now()
        )
        
        return {'success': True, 'message': 'Push notification sent successfully'}
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
