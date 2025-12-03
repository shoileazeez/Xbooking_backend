"""
Email Configuration Test Script
Run with: python test_email.py
Tests if the email backend (Mailjet REST API) is properly configured and working.
"""
import os
import sys
import django

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')
django.setup()

from django.conf import settings
from Xbooking.mailjet_utils import send_mailjet_email


def print_step(step):
    print(f"\n{'='*50}")
    print(f"STEP: {step}")
    print(f"{'='*50}")


def test_email_config():
    """Test email configuration and send a test email"""
    
    print_step("Email Configuration Check")
    
    # Print current email settings (hide sensitive info)
    mailjet_api_key = getattr(settings, 'MAILJET_API_KEY', None)
    mailjet_secret_key = getattr(settings, 'MAILJET_SECRET_KEY', None)
    
    print(f"MAILJET_API_KEY: {mailjet_api_key[:10]}..." if mailjet_api_key else "MAILJET_API_KEY: Not set")
    print(f"MAILJET_SECRET_KEY: {'*' * 20}" if mailjet_secret_key else "MAILJET_SECRET_KEY: Not set")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    if not mailjet_api_key or not mailjet_secret_key:
        print("\n❌ ERROR: Mailjet API credentials not configured!")
        print("Please set MAILJET_API_KEY and MAILJET_SECRET_KEY in your .env file")
        return False
    
    print_step("Send Test Email (Simple)")
    
    # Test recipient - change this to your email
    test_recipient = input("\nEnter the email address to send test email to: ").strip()
    
    if not test_recipient:
        print("❌ No email provided. Exiting.")
        return False
    
    try:
        # Simple text email
        result = send_mailjet_email(
            subject='XBooking Email Test - Simple',
            to_email=test_recipient,
            to_name=test_recipient,
            text_content='This is a simple test email from XBooking to verify your Mailjet REST API configuration is working correctly.\n\nIf you received this, your email setup is working!'
        )
        
        if result.get('success'):
            print(f"✅ Simple email sent successfully to {test_recipient}")
        else:
            print(f"❌ Failed to send simple email: {result.get('error')}")
            return False
            
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
                    <p>This is an <strong>HTML test email</strong> from XBooking using Mailjet REST API.</p>
                    <p>If you can see this formatted message, your email configuration is working correctly with HTML support.</p>
                    <ul>
                        <li>✅ Mailjet API Connection: Working</li>
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
        
        text_content = "XBooking Email Test - HTML\n\nThis is a test email using Mailjet REST API. If you see this, HTML rendering may not be supported by your email client."
        
        result = send_mailjet_email(
            subject='XBooking Email Test - HTML',
            to_email=test_recipient,
            to_name=test_recipient,
            html_content=html_content,
            text_content=text_content
        )
        
        if result.get('success'):
            print(f"✅ HTML email sent successfully to {test_recipient}")
        else:
            print(f"❌ Failed to send HTML email: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send HTML email: {str(e)}")
        return False
    
    print_step("Test Summary")
    print(f"✅ Mailjet REST API configuration appears to be working!")
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
