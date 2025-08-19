"""
Unit Tests for Resend Password Reset Functionality
Tests the serializer logic, validation, and business rules
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from user.serializers.resend_password_reset import ResendPasswordResetSerializer
from user.models import VerificationCode
from user.utils import EmailService
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ResendPasswordResetSerializerUnitTest(TestCase):
    """Unit tests for ResendPasswordResetSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com",
            avatar_url="http://example.com/avatar.jpg"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
        self.valid_data = {
            'email': 'john.doe@example.com'
        }
        
        self.invalid_data = {
            'email': 'nonexistent@example.com'
        }
    
    def test_serializer_validation_with_valid_email(self):
        """Test serializer validation with valid email"""
        # Create an existing verification code (older than 5 minutes)
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        serializer = ResendPasswordResetSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
    def test_serializer_validation_with_invalid_email(self):
        """Test serializer validation with non-existent email"""
        serializer = ResendPasswordResetSerializer(data=self.invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        
    def test_serializer_validation_with_empty_email(self):
        """Test serializer validation with empty email"""
        serializer = ResendPasswordResetSerializer(data={'email': ''})
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        
    def test_serializer_validation_no_existing_request(self):
        """Test validation when no existing password reset request"""
        serializer = ResendPasswordResetSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        
    def test_serializer_validation_recent_request(self):
        """Test validation when recent request exists (within 5 minutes)"""
        # Create a recent verification code
        VerificationCode.objects.create(
            user=self.user,
            code="123456"
        )
        
        serializer = ResendPasswordResetSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_serializer_save_method(self, mock_send_email):
        """Test serializer save method generates new code and sends email"""
        mock_send_email.return_value = True
        
        # Create an old verification code
        old_time = timezone.now() - timedelta(minutes=6)
        old_code = VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        serializer = ResendPasswordResetSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        result = serializer.save()
        
        # Check that new verification code was created
        new_codes = VerificationCode.objects.filter(user=self.user).order_by('-created_at')
        self.assertEqual(new_codes.count(), 1)
        
        new_code = new_codes.first()
        self.assertNotEqual(new_code.code, "123456")  # Should be different from old code
        self.assertEqual(len(new_code.code), 6)
        self.assertFalse(new_code.is_used)
        
        # Check that email was sent
        mock_send_email.assert_called_once_with(
            self.user.email, 
            new_code.code, 
            self.user.full_name
        )
        
        # Check return value
        self.assertIn('message', result)
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_serializer_save_method_email_failure(self, mock_send_email):
        """Test serializer save method when email sending fails"""
        mock_send_email.return_value = False
        
        # Create an old verification code
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        serializer = ResendPasswordResetSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        with self.assertRaises(ValidationError):
            serializer.save()
            
    def test_time_validation_edge_cases(self):
        """Test time validation edge cases"""
        # Test exactly 5 minutes ago (should be valid)
        old_time = timezone.now() - timedelta(minutes=5, seconds=1)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        serializer = ResendPasswordResetSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
    def test_multiple_old_codes_cleanup(self):
        """Test that multiple old codes are properly cleaned up"""
        old_time = timezone.now() - timedelta(minutes=10)
        
        # Create multiple old codes
        codes = []
        for i in range(3):
            code = VerificationCode.objects.create(
                user=self.user,
                code=f"12345{i}",
                created_at=old_time
            )
            codes.append(code)
            
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            serializer = ResendPasswordResetSerializer(data=self.valid_data)
            self.assertTrue(serializer.is_valid())
            serializer.save()
            
            # Should have only one code (the new one)
            remaining_codes = VerificationCode.objects.filter(user=self.user)
            self.assertEqual(remaining_codes.count(), 1)
            
            # New code should be different from all old codes
            new_code = remaining_codes.first()
            old_code_values = [f"12345{i}" for i in range(3)]
            self.assertNotIn(new_code.code, old_code_values)


class ResendPasswordResetBusinessLogicUnitTest(TestCase):
    """Unit tests for business logic validation"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    def test_rate_limiting_logic(self):
        """Test the rate limiting business logic"""
        # Create verification code exactly at the limit
        limit_time = timezone.now() - timedelta(minutes=5)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=limit_time
        )
        
        serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
        
        # Should be invalid due to rate limiting (5 minutes not fully passed)
        self.assertFalse(serializer.is_valid())
        
    def test_code_generation_uniqueness(self):
        """Test that generated codes are unique"""
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        generated_codes = set()
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Generate multiple codes
            for _ in range(10):
                # Clear existing codes
                VerificationCode.objects.filter(user=self.user).delete()
                
                # Create old code
                VerificationCode.objects.create(
                    user=self.user,
                    code="000000",
                    created_at=old_time
                )
                
                serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
                self.assertTrue(serializer.is_valid())
                serializer.save()
                
                new_code = VerificationCode.objects.filter(user=self.user).first()
                generated_codes.add(new_code.code)
                
        # All codes should be unique
        self.assertEqual(len(generated_codes), 10)
        
    def test_used_code_handling(self):
        """Test handling of used verification codes"""
        old_time = timezone.now() - timedelta(minutes=6)
        used_code = VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time,
            is_used=True
        )
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
            self.assertTrue(serializer.is_valid())
            serializer.save()
            
            # Used code should be cleaned up
            self.assertFalse(VerificationCode.objects.filter(id=used_code.id).exists())
            
            # New unused code should exist
            new_codes = VerificationCode.objects.filter(user=self.user, is_used=False)
            self.assertEqual(new_codes.count(), 1)


class ResendPasswordResetValidationUnitTest(TestCase):
    """Unit tests for specific validation scenarios"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    def test_case_insensitive_email_validation(self):
        """Test that email validation is case insensitive"""
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        # Test with uppercase email
        serializer = ResendPasswordResetSerializer(data={'email': 'JOHN.DOE@EXAMPLE.COM'})
        self.assertTrue(serializer.is_valid())
        
    def test_email_whitespace_handling(self):
        """Test that email whitespace is properly handled"""
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        # Test with whitespace around email
        serializer = ResendPasswordResetSerializer(data={'email': '  john.doe@example.com  '})
        self.assertTrue(serializer.is_valid())
        
    def test_inactive_user_handling(self):
        """Test handling of inactive users"""
        self.user.is_active = False
        self.user.save()
        
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        serializer = ResendPasswordResetSerializer(data={'email': self.user.email})
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        
    def test_multiple_users_same_timing(self):
        """Test that resend logic works correctly with multiple users"""
        # Create second user
        user2 = User.objects.create(
            full_name="Jane Smith",
            email="jane.smith@example.com"
        )
        user2.set_password("SecurePass456!")
        user2.save()
        
        old_time = timezone.now() - timedelta(minutes=6)
        
        # Create old codes for both users
        VerificationCode.objects.create(user=self.user, code="111111", created_at=old_time)
        VerificationCode.objects.create(user=user2, code="222222", created_at=old_time)
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Resend for first user
            serializer1 = ResendPasswordResetSerializer(data={'email': self.user.email})
            self.assertTrue(serializer1.is_valid())
            serializer1.save()
            
            # Resend for second user
            serializer2 = ResendPasswordResetSerializer(data={'email': user2.email})
            self.assertTrue(serializer2.is_valid())
            serializer2.save()
            
            # Each user should have exactly one verification code
            user1_codes = VerificationCode.objects.filter(user=self.user)
            user2_codes = VerificationCode.objects.filter(user=user2)
            
            self.assertEqual(user1_codes.count(), 1)
            self.assertEqual(user2_codes.count(), 1)
            
            # Codes should be different
            self.assertNotEqual(user1_codes.first().code, user2_codes.first().code)
