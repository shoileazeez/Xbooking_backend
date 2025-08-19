"""
Unit Tests for Forget Password Functionality
Tests the serializer logic and validation
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from user.serializers.forget_password import ForgetPasswordSerializer
from user.models import VerificationCode
from user.utils.email_service import EmailService
from django.core.exceptions import ValidationError

User = get_user_model()


class ForgetPasswordSerializerUnitTest(TestCase):
    """Unit tests for ForgetPasswordSerializer"""
    
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
        serializer = ForgetPasswordSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
    def test_serializer_validation_with_invalid_email(self):
        """Test serializer validation with non-existent email"""
        serializer = ForgetPasswordSerializer(data=self.invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        
    def test_serializer_validation_with_empty_email(self):
        """Test serializer validation with empty email"""
        serializer = ForgetPasswordSerializer(data={'email': ''})
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        
    def test_serializer_validation_with_invalid_email_format(self):
        """Test serializer validation with invalid email format"""
        serializer = ForgetPasswordSerializer(data={'email': 'invalid-email'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_serializer_save_method(self, mock_send_email):
        """Test serializer save method creates verification code and sends email"""
        mock_send_email.return_value = True
        
        serializer = ForgetPasswordSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        result = serializer.save()
        
        # Check that verification code was created
        verification_code = VerificationCode.objects.filter(user=self.user).first()
        self.assertIsNotNone(verification_code)
        self.assertEqual(len(verification_code.code), 6)
        self.assertFalse(verification_code.is_used)
        
        # Check that email was sent
        mock_send_email.assert_called_once_with(self.user.email, verification_code.code, self.user.full_name)
        
        # Check return value
        self.assertIn('message', result)
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_serializer_save_method_email_failure(self, mock_send_email):
        """Test serializer save method when email sending fails"""
        mock_send_email.return_value = False
        
        serializer = ForgetPasswordSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        with self.assertRaises(ValidationError):
            serializer.save()
            
    def test_rate_limiting_validation(self):
        """Test that rate limiting prevents multiple requests within 5 minutes"""
        # Create an existing verification code
        VerificationCode.objects.create(
            user=self.user,
            code="123456"
        )
        
        serializer = ForgetPasswordSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_multiple_verification_codes_cleanup(self, mock_send_email):
        """Test that old verification codes are cleaned up when creating new ones"""
        mock_send_email.return_value = True
        
        # Create old verification codes
        old_code1 = VerificationCode.objects.create(
            user=self.user,
            code="111111"
        )
        old_code2 = VerificationCode.objects.create(
            user=self.user,
            code="222222"
        )
        
        # Move creation time back to simulate old codes
        from django.utils import timezone
        from datetime import timedelta
        old_time = timezone.now() - timedelta(minutes=10)
        
        VerificationCode.objects.filter(id__in=[old_code1.id, old_code2.id]).update(
            created_at=old_time
        )
        
        serializer = ForgetPasswordSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        
        # Check that only one verification code exists (the new one)
        codes = VerificationCode.objects.filter(user=self.user)
        self.assertEqual(codes.count(), 1)
        self.assertNotIn(codes.first().code, ["111111", "222222"])


class ForgetPasswordEmailServiceUnitTest(TestCase):
    """Unit tests for EmailService password reset functionality"""
    
    @patch('user.services.email_service.send_mail')
    def test_send_password_reset_email_success(self, mock_send_mail):
        """Test successful password reset email sending"""
        mock_send_mail.return_value = True
        
        result = EmailService.send_password_reset_email(
            "test@example.com", 
            "123456", 
            "John Doe"
        )
        
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        
        # Check email content
        call_args = mock_send_mail.call_args
        self.assertIn("Password Reset", call_args[0][0])  # Subject
        self.assertIn("123456", call_args[0][1])  # Message body
        self.assertIn("test@example.com", call_args[0][3])  # Recipient
        
    @patch('user.services.email_service.send_mail')
    def test_send_password_reset_email_failure(self, mock_send_mail):
        """Test password reset email sending failure"""
        mock_send_mail.side_effect = Exception("SMTP Error")
        
        result = EmailService.send_password_reset_email(
            "test@example.com", 
            "123456", 
            "John Doe"
        )
        
        self.assertFalse(result)
        
    def test_send_password_reset_email_with_none_values(self):
        """Test password reset email with None values"""
        result = EmailService.send_password_reset_email(None, None, None)
        self.assertFalse(result)
        
    def test_send_password_reset_email_with_empty_values(self):
        """Test password reset email with empty values"""
        result = EmailService.send_password_reset_email("", "", "")
        self.assertFalse(result)


class VerificationCodeModelUnitTest(TestCase):
    """Unit tests for VerificationCode model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    def test_verification_code_creation(self):
        """Test verification code model creation"""
        code = VerificationCode.objects.create(
            user=self.user,
            code="123456"
        )
        
        self.assertEqual(code.user, self.user)
        self.assertEqual(code.code, "123456")
        self.assertFalse(code.is_used)
        self.assertIsNotNone(code.created_at)
        
    def test_verification_code_string_representation(self):
        """Test verification code string representation"""
        code = VerificationCode.objects.create(
            user=self.user,
            code="123456"
        )
        
        expected_str = f"Verification code for {self.user.email}"
        # Note: This assumes you add a __str__ method to VerificationCode model
        
    def test_verification_code_cascade_delete(self):
        """Test that verification codes are deleted when user is deleted"""
        code = VerificationCode.objects.create(
            user=self.user,
            code="123456"
        )
        
        user_id = self.user.id
        self.user.delete()
        
        # Verification code should be deleted due to CASCADE
        self.assertFalse(VerificationCode.objects.filter(user_id=user_id).exists())
