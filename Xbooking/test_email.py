"""
Email Configuration Test Script
Run with: python test_email.py
Tests if the email backend (Mailjet) is properly configured and working.
"""
import os
import sys
import django

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')
django.setup()

from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings


def print_step(step):
    print(f"\n{'='*50}")
    print(f"STEP: {step}")
    print(f"{'='*50}")


def test_email_config():
    """Test email configuration and send a test email"""
    
    print_step("Email Configuration Check")
    
    # Print current email settings (hide sensitive info)
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_USE_SSL: {getattr(settings, 'EMAIL_USE_SSL', False)}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER[:10]}..." if settings.EMAIL_HOST_USER else "EMAIL_HOST_USER: Not set")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    print_step("Send Test Email (Simple)")
    
    # Test recipient - change this to your email
    test_recipient = input("\nEnter the email address to send test email to: ").strip()
    
    if not test_recipient:
        print("❌ No email provided. Exiting.")
        return False
    
    try:
        # Simple text email
        result = send_mail(
            subject='XBooking Email Test - Simple',
            message='This is a simple test email from XBooking to verify your email configuration is working correctly.\n\nIf you received this, your email setup is working!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_recipient],
            fail_silently=False,
        )
        
        if result:
            print(f"✅ Simple email sent successfully to {test_recipient}")
        else:
            print(f"⚠️ send_mail returned 0 - email may not have been sent")
            
    except Exception as e:
        print(f"❌ Failed to send simple email: {str(e)}")
        return False
    
    print_step("Send Test Email (HTML)")
    
    try:
        # HTML email
        html_content = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }
                .container { background-color: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto; }
                .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
                .content { padding: 20px; }
                .footer { text-align: center; color: #888; font-size: 12px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 XBooking Email Test</h1>
                </div>
                <div class="content">
                    <h2>HTML Email Test Successful!</h2>
                    <p>This is an <strong>HTML test email</strong> from XBooking.</p>
                    <p>If you can see this formatted message, your email configuration is working correctly with HTML support.</p>
                    <ul>
                        <li>✅ SMTP Connection: Working</li>
                        <li>✅ Authentication: Valid</li>
                        <li>✅ HTML Rendering: Supported</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>XBooking - Space Booking Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = "XBooking Email Test - HTML\n\nThis is a test email. If you see this, HTML rendering may not be supported by your email client."
        
        email = EmailMultiAlternatives(
            subject='XBooking Email Test - HTML',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[test_recipient]
        )
        email.attach_alternative(html_content, "text/html")
        result = email.send()
        
        if result:
            print(f"✅ HTML email sent successfully to {test_recipient}")
        else:
            print(f"⚠️ EmailMultiAlternatives.send() returned 0 - email may not have been sent")
            
    except Exception as e:
        print(f"❌ Failed to send HTML email: {str(e)}")
        return False
    
    print_step("Test Summary")
    print(f"✅ Email configuration appears to be working!")
    print(f"✅ Check {test_recipient} inbox (and spam folder) for test emails")
    print(f"\n🎉 Email test completed successfully!")
    
    return True


if __name__ == "__main__":
    try:
        success = test_email_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
