"""
Integration Tests for Resend Password Reset Functionality
Tests the complete flow including database interactions, email sending, and business logic
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import transaction
from unittest.mock import patch, MagicMock
from user.models import VerificationCode
from user.serializers.resend_password_reset import ResendPasswordResetSerializer
from user.utils import EmailService
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ResendPasswordResetIntegrationTest(TestCase):
    """Integration tests for the complete resend password reset flow"""
    
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
    def test_complete_resend_password_reset_flow(self, mock_send_email):
        """Test the complete resend flow from validation to email sending"""
        mock_send_email.return_value = True
        
        # Create an old verification code
        old_time = timezone.now() - timedelta(minutes=6)
        old_code = VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        # Test data
        data = {'email': 'john.doe@example.com'}
        
        # Initialize serializer
        serializer = ResendPasswordResetSerializer(data=data)
        
        # Validate
        self.assertTrue(serializer.is_valid())
        
        # Save (this should create new verification code and send email)
        result = serializer.save()
        
        # Verify old code was deleted
        self.assertFalse(VerificationCode.objects.filter(id=old_code.id).exists())
        
        # Verify new code was created
        new_codes = VerificationCode.objects.filter(user=self.user)
        self.assertEqual(new_codes.count(), 1)
        
        new_code = new_codes.first()
        self.assertNotEqual(new_code.code, "123456")  # Should be different
        self.assertEqual(len(new_code.code), 6)
        self.assertFalse(new_code.is_used)
        
        # Verify email was sent with correct parameters
        mock_send_email.assert_called_once_with(
            self.user.email,
            new_code.code,
            self.user.full_name
        )
        
        # Verify response
        self.assertIsInstance(result, dict)
        self.assertIn('message', result)
        
    def test_resend_password_reset_complete_workflow(self):
        """Test the complete workflow: forget -> resend -> confirm"""
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Step 1: Initial forget password request
            from user.serializers.forget_password import ForgetPasswordSerializer
            
            forget_serializer = ForgetPasswordSerializer(data={'email': self.user.email})
            self.assertTrue(forget_serializer.is_valid())
            forget_serializer.save()
            
            initial_code = VerificationCode.objects.filter(user=self.user).first()
            self.assertIsNotNone(initial_code)
            
            # Step 2: Move time forward to allow resend (simulate 6 minutes)
            old_time = timezone.now() - timedelta(minutes=6)
            VerificationCode.objects.filter(user=self.user).update(created_at=old_time)
            
            # Step 3: Resend password reset
            resend_serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
            self.assertTrue(resend_serializer.is_valid())
            resend_serializer.save()
            
            # Verify new code was generated
            new_codes = VerificationCode.objects.filter(user=self.user)
            self.assertEqual(new_codes.count(), 1)
            
            new_code = new_codes.first()
            self.assertNotEqual(new_code.code, initial_code.code)
            
            # Step 4: Verify the new code can be used for password reset
            from user.serializers.password_reset_confirm import PasswordResetConfirmSerializer
            
            reset_data = {
                'email': self.user.email,
                'verification_code': new_code.code,
                'new_password': 'NewPassword123!',
                'confirm_new_password': 'NewPassword123!'
            }
            
            reset_serializer = PasswordResetConfirmSerializer(data=reset_data)
            self.assertTrue(reset_serializer.is_valid())
            reset_serializer.save()
            
            # Verify password was changed
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password('NewPassword123!'))
            
    def test_resend_with_multiple_users_integration(self):
        """Test resend functionality with multiple users"""
        # Create additional users
        users = []
        for i in range(3):
            user = User.objects.create(
                full_name=f"User {i}",
                email=f"user{i}@example.com"
            )
            user.set_password("SecurePass123!")
            user.save()
            users.append(user)
            
        old_time = timezone.now() - timedelta(minutes=6)
        
        # Create old codes for all users
        for user in users:
            VerificationCode.objects.create(
                user=user,
                code=f"12345{user.id}",
                created_at=old_time
            )
            
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Resend for all users
            for user in users:
                serializer = ResendPasswordResetSerializer(data={'email': user.email})
                self.assertTrue(serializer.is_valid())
                serializer.save()
                
            # Verify each user has exactly one new code
            for user in users:
                codes = VerificationCode.objects.filter(user=user)
                self.assertEqual(codes.count(), 1)
                
                code = codes.first()
                self.assertNotEqual(code.code, f"12345{user.id}")  # Should be new
                
    def test_resend_database_consistency(self):
        """Test database consistency during resend operations"""
        old_time = timezone.now() - timedelta(minutes=6)
        
        # Create multiple old codes for the same user
        old_codes = []
        for i in range(3):
            code = VerificationCode.objects.create(
                user=self.user,
                code=f"old_code_{i}",
                created_at=old_time
            )
            old_codes.append(code)
            
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
            self.assertTrue(serializer.is_valid())
            serializer.save()
            
            # Verify all old codes were deleted
            for old_code in old_codes:
                self.assertFalse(VerificationCode.objects.filter(id=old_code.id).exists())
                
            # Verify exactly one new code exists
            new_codes = VerificationCode.objects.filter(user=self.user)
            self.assertEqual(new_codes.count(), 1)
            
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_resend_transaction_rollback(self, mock_send_email):
        """Test that database changes are rolled back on email failure"""
        mock_send_email.return_value = False  # Simulate email failure
        
        old_time = timezone.now() - timedelta(minutes=6)
        old_code = VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
        self.assertTrue(serializer.is_valid())
        
        # Should raise exception due to email failure
        with self.assertRaises(Exception):
            serializer.save()
            
        # Verify old code still exists (transaction rolled back)
        self.assertTrue(VerificationCode.objects.filter(id=old_code.id).exists())
        
    def test_resend_rate_limiting_integration(self):
        """Test rate limiting integration with database and time validation"""
        # Create a recent code (within 5 minutes)
        recent_time = timezone.now() - timedelta(minutes=3)
        recent_code = VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=recent_time
        )
        
        # Attempt to resend should fail
        serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
        self.assertFalse(serializer.is_valid())
        
        # Verify original code is unchanged
        recent_code.refresh_from_db()
        self.assertEqual(recent_code.code, "123456")
        
        # Move time forward to allow resend
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.filter(id=recent_code.id).update(created_at=old_time)
        
        # Now resend should work
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
            self.assertTrue(serializer.is_valid())
            serializer.save()
            
            # Verify old code was replaced
            self.assertFalse(VerificationCode.objects.filter(id=recent_code.id).exists())


class ResendPasswordResetEmailIntegrationTest(TestCase):
    """Integration tests for email functionality in resend flow"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    def test_resend_email_content_integration(self):
        """Test that resend emails contain correct content"""
        from django.conf import settings
        original_backend = settings.EMAIL_BACKEND
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        try:
            old_time = timezone.now() - timedelta(minutes=6)
            VerificationCode.objects.create(
                user=self.user,
                code="123456",
                created_at=old_time
            )
            
            serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
            self.assertTrue(serializer.is_valid())
            serializer.save()
            
            # Check email was sent
            self.assertEqual(len(mail.outbox), 1)
            
            sent_email = mail.outbox[0]
            new_code = VerificationCode.objects.filter(user=self.user).first()
            
            # Verify email content
            self.assertIn("Password Reset", sent_email.subject)
            self.assertIn(new_code.code, sent_email.body)
            self.assertIn(self.user.full_name, sent_email.body)
            self.assertIn(self.user.email, sent_email.to)
            
        finally:
            settings.EMAIL_BACKEND = original_backend
            mail.outbox = []
            
    def test_resend_email_template_variables(self):
        """Test that email templates receive correct variables"""
        from django.conf import settings
        original_backend = settings.EMAIL_BACKEND
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        try:
            old_time = timezone.now() - timedelta(minutes=6)
            VerificationCode.objects.create(
                user=self.user,
                code="123456",
                created_at=old_time
            )
            
            serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
            self.assertTrue(serializer.is_valid())
            serializer.save()
            
            sent_email = mail.outbox[0]
            new_code = VerificationCode.objects.filter(user=self.user).first()
            
            # Verify all template variables were replaced
            self.assertIn(self.user.full_name, sent_email.body)
            self.assertIn(new_code.code, sent_email.body)
            self.assertNotIn("{{", sent_email.body)  # No unrendered variables
            self.assertNotIn("}}", sent_email.body)
            
        finally:
            settings.EMAIL_BACKEND = original_backend
            mail.outbox = []


class ResendPasswordResetConcurrencyIntegrationTest(TransactionTestCase):
    """Test concurrent resend scenarios"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_concurrent_resend_requests(self, mock_send_email):
        """Test handling of concurrent resend requests"""
        mock_send_email.return_value = True
        
        # Create old verification code
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        def create_resend_request():
            serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
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
            thread = threading.Thread(target=lambda: results.append(create_resend_request()))
            threads.append(thread)
            
        # Start all threads
        for thread in threads:
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        # Only one request should succeed
        successful_requests = sum(results)
        self.assertEqual(successful_requests, 1)
        
        # Only one verification code should exist
        codes = VerificationCode.objects.filter(user=self.user)
        self.assertEqual(codes.count(), 1)
