"""
Mailjet REST API Utility for sending emails
Replaces SMTP email sending with Mailjet REST API
"""
import requests
import logging
from django.conf import settings
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class MailjetEmailService:
    """
    Service class for sending emails via Mailjet REST API
    """
    
    MAILJET_API_URL = "https://api.mailjet.com/v3.1/send"
    
    @classmethod
    def _get_credentials(cls):
        """Get Mailjet API credentials from settings"""
        api_key = getattr(settings, 'MAILJET_API_KEY', '')
        secret_key = getattr(settings, 'MAILJET_SECRET_KEY', '')
        
        if not api_key or not secret_key:
            raise ValueError("MAILJET_API_KEY and MAILJET_SECRET_KEY must be set in settings")
        
        return api_key, secret_key
    
    @classmethod
    def send_email(
        cls,
        subject: str,
        to_email: str,
        to_name: str = "",
        html_content: str = "",
        text_content: str = "",
        from_email: str = None,
        from_name: str = "XBooking",
        attachments: List[Dict] = None,
        cc: List[Dict] = None,
        bcc: List[Dict] = None,
    ) -> Dict:
        """
        Send email using Mailjet REST API
        
        Args:
            subject: Email subject
            to_email: Recipient email address
            to_name: Recipient name (optional)
            html_content: HTML version of email body
            text_content: Plain text version of email body
            from_email: Sender email address (defaults to DEFAULT_FROM_EMAIL)
            from_name: Sender name
            attachments: List of attachment dicts with 'ContentType', 'Filename', 'Base64Content'
            cc: List of CC recipients [{'Email': 'email@example.com', 'Name': 'Name'}]
            bcc: List of BCC recipients [{'Email': 'email@example.com', 'Name': 'Name'}]
            
        Returns:
            dict: Response from Mailjet API with success status and message
        """
        try:
            api_key, secret_key = cls._get_credentials()
            
            # Default from email
            if not from_email:
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@xbooking.com')
            
            # Build message payload
            message = {
                "From": {
                    "Email": from_email,
                    "Name": from_name
                },
                "To": [
                    {
                        "Email": to_email,
                        "Name": to_name or to_email
                    }
                ],
                "Subject": subject,
            }
            
            # Add HTML and/or text content
            if html_content:
                message["HTMLPart"] = html_content
            if text_content:
                message["TextPart"] = text_content
            
            # Add CC if provided
            if cc:
                message["Cc"] = cc
            
            # Add BCC if provided
            if bcc:
                message["Bcc"] = bcc
            
            # Add attachments if provided
            if attachments:
                message["Attachments"] = attachments
            
            # Prepare request payload
            payload = {
                "Messages": [message]
            }
            
            # Make API request
            response = requests.post(
                cls.MAILJET_API_URL,
                auth=(api_key, secret_key),
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Email sent successfully to {to_email}: {subject}")
                return {
                    'success': True,
                    'message': 'Email sent successfully',
                    'response': result
                }
            else:
                error_msg = response.text
                logger.error(f"Failed to send email to {to_email}: {response.status_code} - {error_msg}")
                return {
                    'success': False,
                    'error': f"Mailjet API error: {response.status_code}",
                    'details': error_msg
                }
                
        except ValueError as ve:
            logger.error(f"Configuration error: {str(ve)}")
            return {
                'success': False,
                'error': str(ve)
            }
        except Exception as e:
            logger.error(f"Exception sending email to {to_email}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def send_bulk_email(
        cls,
        subject: str,
        recipients: List[Dict],  # [{'email': 'user@example.com', 'name': 'User Name'}]
        html_content: str = "",
        text_content: str = "",
        from_email: str = None,
        from_name: str = "XBooking",
    ) -> Dict:
        """
        Send bulk email to multiple recipients
        
        Args:
            subject: Email subject
            recipients: List of recipient dicts with 'email' and 'name' keys
            html_content: HTML version of email body
            text_content: Plain text version of email body
            from_email: Sender email address
            from_name: Sender name
            
        Returns:
            dict: Response summary with counts of successful/failed sends
        """
        try:
            api_key, secret_key = cls._get_credentials()
            
            if not from_email:
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@xbooking.com')
            
            # Build messages array
            messages = []
            for recipient in recipients:
                message = {
                    "From": {
                        "Email": from_email,
                        "Name": from_name
                    },
                    "To": [
                        {
                            "Email": recipient.get('email'),
                            "Name": recipient.get('name', recipient.get('email'))
                        }
                    ],
                    "Subject": subject,
                }
                
                if html_content:
                    message["HTMLPart"] = html_content
                if text_content:
                    message["TextPart"] = text_content
                
                messages.append(message)
            
            # Prepare request payload
            payload = {
                "Messages": messages
            }
            
            # Make API request
            response = requests.post(
                cls.MAILJET_API_URL,
                auth=(api_key, secret_key),
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Bulk email sent to {len(recipients)} recipients")
                return {
                    'success': True,
                    'message': f'Bulk email sent to {len(recipients)} recipients',
                    'response': result
                }
            else:
                error_msg = response.text
                logger.error(f"Failed to send bulk email: {response.status_code} - {error_msg}")
                return {
                    'success': False,
                    'error': f"Mailjet API error: {response.status_code}",
                    'details': error_msg
                }
                
        except Exception as e:
            logger.error(f"Exception sending bulk email: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Convenience function for simple email sending
def send_mailjet_email(subject, to_email, html_content="", text_content="", **kwargs):
    """
    Convenience function to send a single email via Mailjet
    
    Args:
        subject: Email subject
        to_email: Recipient email
        html_content: HTML email body
        text_content: Plain text email body
        **kwargs: Additional arguments passed to MailjetEmailService.send_email()
        
    Returns:
        dict: Response from Mailjet API
    """
    return MailjetEmailService.send_email(
        subject=subject,
        to_email=to_email,
        html_content=html_content,
        text_content=text_content,
        **kwargs
    )
