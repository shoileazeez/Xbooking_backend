"""
Integration Tests for Forget Password Functionality
Tests the complete flow including database interactions, email sending, and view logic
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import transaction
from unittest.mock import patch, MagicMock
from user.models import VerificationCode
from user.serializers.forget_password import ForgetPasswordSerializer
from user.views.forget_password import ForgetPasswordView
from user.utils import EmailService
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ForgetPasswordIntegrationTest(TestCase):
    """Integration tests for the complete forget password flow"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com",
            avatar_url="http://example.com/avatar.jpg"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_complete_forget_password_flow(self, mock_send_email):
        """Test the complete forget password flow from serializer to database"""
        mock_send_email.return_value = True
        
        # Test data
        data = {'email': 'john.doe@example.com'}
        
        # Initialize serializer
        serializer = ForgetPasswordSerializer(data=data)
        
        # Validate
        self.assertTrue(serializer.is_valid())
        
        # Save (this should create verification code and send email)
        result = serializer.save()
        
        # Verify database changes
        verification_codes = VerificationCode.objects.filter(user=self.user)
        self.assertEqual(verification_codes.count(), 1)
        
        verification_code = verification_codes.first()
        self.assertEqual(len(verification_code.code), 6)
        self.assertFalse(verification_code.is_used)
        self.assertTrue(verification_code.code.isdigit())
        
        # Verify email was sent with correct parameters
        mock_send_email.assert_called_once_with(
            self.user.email,
            verification_code.code,
            self.user.full_name
        )
        
        # Verify response
        self.assertIsInstance(result, dict)
        self.assertIn('message', result)
        
    def test_forget_password_with_multiple_users(self):
        """Test forget password with multiple users to ensure isolation"""
        # Create second user
        user2 = User.objects.create(
            full_name="Jane Smith",
            email="jane.smith@example.com"
        )
        user2.set_password("SecurePass456!")
        user2.save()
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Request password reset for first user
            serializer1 = ForgetPasswordSerializer(data={'email': 'john.doe@example.com'})
            self.assertTrue(serializer1.is_valid())
            serializer1.save()
            
            # Request password reset for second user
            serializer2 = ForgetPasswordSerializer(data={'email': 'jane.smith@example.com'})
            self.assertTrue(serializer2.is_valid())
            serializer2.save()
            
            # Verify both users have separate verification codes
            user1_codes = VerificationCode.objects.filter(user=self.user)
            user2_codes = VerificationCode.objects.filter(user=user2)
            
            self.assertEqual(user1_codes.count(), 1)
            self.assertEqual(user2_codes.count(), 1)
            self.assertNotEqual(user1_codes.first().code, user2_codes.first().code)
            
    def test_forget_password_rate_limiting_integration(self):
        """Test rate limiting in the complete integration flow"""
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # First request should succeed
            serializer1 = ForgetPasswordSerializer(data={'email': 'john.doe@example.com'})
            self.assertTrue(serializer1.is_valid())
            serializer1.save()
            
            # Second request within 5 minutes should fail
            serializer2 = ForgetPasswordSerializer(data={'email': 'john.doe@example.com'})
            self.assertFalse(serializer2.is_valid())
            self.assertIn('non_field_errors', serializer2.errors)
            
    def test_forget_password_cleanup_old_codes(self):
        """Test that old verification codes are cleaned up"""
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Create old verification codes manually
            old_time = timezone.now() - timedelta(minutes=10)
            old_code1 = VerificationCode.objects.create(
                user=self.user,
                code="111111",
                created_at=old_time
            )
            old_code2 = VerificationCode.objects.create(
                user=self.user,
                code="222222",
                created_at=old_time
            )
            
            # Request new password reset
            serializer = ForgetPasswordSerializer(data={'email': 'john.doe@example.com'})
            self.assertTrue(serializer.is_valid())
            serializer.save()
            
            # Verify only the new code exists
            current_codes = VerificationCode.objects.filter(user=self.user)
            self.assertEqual(current_codes.count(), 1)
            
            new_code = current_codes.first()
            self.assertNotIn(new_code.code, ["111111", "222222"])
            
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_forget_password_database_transaction(self, mock_send_email):
        """Test that database operations are properly wrapped in transactions"""
        # Simulate email sending failure
        mock_send_email.return_value = False
        
        initial_code_count = VerificationCode.objects.count()
        
        serializer = ForgetPasswordSerializer(data={'email': 'john.doe@example.com'})
        self.assertTrue(serializer.is_valid())
        
        # This should raise an exception and rollback any database changes
        with self.assertRaises(Exception):
            serializer.save()
            
        # Verify no verification code was created due to rollback
        final_code_count = VerificationCode.objects.count()
        self.assertEqual(initial_code_count, final_code_count)


class ForgetPasswordEmailIntegrationTest(TestCase):
    """Integration tests for email functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    def test_email_service_with_django_mail_backend(self):
        """Test email service integration with Django's email backend"""
        # Use Django's locmem email backend for testing
        from django.conf import settings
        original_backend = settings.EMAIL_BACKEND
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        try:
            result = EmailService.send_password_reset_email(
                "john.doe@example.com",
                "123456",
                "John Doe"
            )
            
            # Should succeed with locmem backend
            self.assertTrue(result)
            
            # Check that email was added to Django's mail outbox
            self.assertEqual(len(mail.outbox), 1)
            
            sent_email = mail.outbox[0]
            self.assertIn("Password Reset", sent_email.subject)
            self.assertIn("123456", sent_email.body)
            self.assertIn("john.doe@example.com", sent_email.to)
            
        finally:
            settings.EMAIL_BACKEND = original_backend
            mail.outbox = []  # Clear outbox
            
    def test_email_template_rendering_integration(self):
        """Test that email templates are properly rendered with context"""
        from django.conf import settings
        original_backend = settings.EMAIL_BACKEND
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        try:
            EmailService.send_password_reset_email(
                "john.doe@example.com",
                "123456",
                "John Doe"
            )
            
            sent_email = mail.outbox[0]
            
            # Check that template variables were properly replaced
            self.assertIn("John Doe", sent_email.body)
            self.assertIn("123456", sent_email.body)
            self.assertNotIn("{{", sent_email.body)  # No unrendered template variables
            self.assertNotIn("}}", sent_email.body)
            
        finally:
            settings.EMAIL_BACKEND = original_backend
            mail.outbox = []


class ForgetPasswordConcurrencyTest(TransactionTestCase):
    """Test concurrent access scenarios"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_concurrent_forget_password_requests(self, mock_send_email):
        """Test handling of concurrent forget password requests"""
        mock_send_email.return_value = True
        
        def create_request():
            serializer = ForgetPasswordSerializer(data={'email': 'john.doe@example.com'})
            if serializer.is_valid():
                try:
                    serializer.save()
                    return True
                except Exception:
                    return False
            return False
        
        # Simulate concurrent requests
        import threading
        results = []
        threads = []
        
        for i in range(3):
            thread = threading.Thread(target=lambda: results.append(create_request()))
            threads.append(thread)
            
        # Start all threads
        for thread in threads:
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Only one request should succeed due to rate limiting
        successful_requests = sum(results)
        self.assertEqual(successful_requests, 1)
        
        # Only one verification code should exist
        verification_codes = VerificationCode.objects.filter(user=self.user)
        self.assertEqual(verification_codes.count(), 1)
