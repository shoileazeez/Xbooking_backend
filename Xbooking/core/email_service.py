"""
Email Notification Service
Handles all email sending via EventBus subscription
"""
import logging
from typing import Dict, Any
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.services import EventBus, Event, EventTypes

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service that subscribes to EMAIL_SENT events
    """
    
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str, text_content: str = None):
        """
        Send email using Django's email backend
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text fallback (optional)
        """
        try:
            if text_content is None:
                text_content = strip_tags(html_content)
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_content,
                fail_silently=False,
            )
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def handle_email_event(event: Event):
        """
        Handle EMAIL_SENT events
        
        Event data should contain:
        - user_id: User ID
        - notification_type: Type of notification
        - title: Email subject
        - message: Email message
        - Additional context based on notification_type
        """
        try:
            data = event.data
            notification_type = data.get('notification_type')
            
            # Get user email
            from user.models import User
            user_id = data.get('user_id')
            if not user_id:
                logger.error("No user_id in email event")
                return
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.error(f"User not found: {user_id}")
                return
            
            # Prepare email content based on notification type
            subject = data.get('title', 'Notification from Xbooking')
            context = {
                'user': user,
                'title': data.get('title'),
                'message': data.get('message'),
                **data
            }
            
            # Render template based on notification type
            template_map = {
                'workspace_invite': 'emails/workspace_invite.html',
                'workspace_member_added': 'emails/workspace_member_added.html',
                'password_changed': 'emails/password_changed.html',
                'onboarding_completed': 'emails/onboarding_completed.html',
                'booking_created': 'emails/booking_created.html',
                'booking_confirmed': 'emails/booking_confirmed.html',
                'booking_cancelled': 'emails/booking_cancelled.html',
                'payment_completed': 'emails/payment_completed.html',
                'qr_code_generated': 'emails/qr_code_generated.html',
            }
            
            template = template_map.get(notification_type, 'emails/generic.html')
            
            try:
                html_content = render_to_string(template, context)
            except Exception as e:
                logger.warning(f"Template not found, using generic: {str(e)}")
                html_content = f"""
                <html>
                <body>
                    <h2>{context['title']}</h2>
                    <p>{context['message']}</p>
                </body>
                </html>
                """
            
            # Send email
            EmailService.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content
            )
            
            logger.info(f"Processed email event: {notification_type} for user {user.email}")
        
        except Exception as e:
            logger.error(f"Error handling email event: {str(e)}")
    
    @classmethod
    def initialize(cls):
        """
        Initialize email service by subscribing to EMAIL_SENT events
        """
        EventBus.subscribe(EventTypes.EMAIL_SENT, cls.handle_email_event)
        logger.info("EmailService initialized and subscribed to EMAIL_SENT events")
