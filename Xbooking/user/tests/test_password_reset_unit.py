"""
Unit tests for password reset functionality.
Tests individual components and methods in isolation.
"""

import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError

from user.serializers.forget_password import ForgetPasswordSerializer
from user.serializers.password_reset_confirm import PasswordResetConfirmSerializer
from user.serializers.resend_password_reset import ResendPasswordResetSerializer
from user.utils.email_service import EmailService
from user.utils.code_utils import (
    generate_verification_code,
    is_valid_verification_code,
    has_valid_reset_code
)
from user.validators.password_validators import validate_password_strength

User = get_user_model()


class CodeUtilsTestCase(TestCase):
    """Test password reset code utility functions"""
    
    def test_generate_verification_code(self):
        """Test verification code generation"""
        code = generate_verification_code()
        
        # Should be 6 digits
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        
        # Should be unique each time
        code2 = generate_verification_code()
        self.assertNotEqual(code, code2)
    
    def test_is_valid_verification_code(self):
        """Test verification code validation"""
        # Valid codes
        self.assertTrue(is_valid_verification_code("123456"))
        self.assertTrue(is_valid_verification_code("000000"))
        self.assertTrue(is_valid_verification_code("999999"))
        
        # Invalid codes
        self.assertFalse(is_valid_verification_code("12345"))   # Too short
        self.assertFalse(is_valid_verification_code("1234567")) # Too long
        self.assertFalse(is_valid_verification_code("12345a"))  # Contains letter
        self.assertFalse(is_valid_verification_code(""))        # Empty
        self.assertFalse(is_valid_verification_code(None))      # None


class PasswordValidatorsTestCase(TestCase):
    """Test password validation functions"""
    
    def test_validate_password_strength_valid(self):
        """Test password strength validation with valid passwords"""
        valid_passwords = [
            "Password123!",
            "MySecure@Pass1",
            "Complex#Pass9",
            "StrongPwd@2024"
        ]
        
        for password in valid_passwords:
            with self.subTest(password=password):
                try:
                    validate_password_strength(password)
                except ValidationError:
                    self.fail(f"Valid password '{password}' failed validation")
    
    def test_validate_password_strength_invalid(self):
        """Test password strength validation with invalid passwords"""
        invalid_passwords = [
            ("short", "Password must be at least 8 characters long"),
            ("nouppercase1!", "Password must contain at least one uppercase letter"),
            ("NOLOWERCASE1!", "Password must contain at least one lowercase letter"),
            ("NoDigits!@#", "Password must contain at least one digit"),
            ("NoSpecial123", "Password must contain at least one special character"),
        ]
        
        for password, expected_error in invalid_passwords:
            with self.subTest(password=password):
                with self.assertRaises(ValidationError) as cm:
                    validate_password_strength(password)
                self.assertIn(expected_error, str(cm.exception))


class ForgetPasswordSerializerTestCase(TestCase):
    """Test ForgetPasswordSerializer unit functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="test@example.com",
            full_name="Test User",
            password="TestPass123!"
        )
    
    def test_serializer_valid_data(self):
        """Test serializer with valid email"""
        data = {"email": "test@example.com"}
        serializer = ForgetPasswordSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "test@example.com")
    
    def test_serializer_invalid_email_format(self):
        """Test serializer with invalid email format"""
        data = {"email": "invalid-email"}
        serializer = ForgetPasswordSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
    
    def test_serializer_nonexistent_email(self):
        """Test serializer with non-existent email"""
        data = {"email": "nonexistent@example.com"}
        serializer = ForgetPasswordSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
    
    def test_serializer_missing_email(self):
        """Test serializer without email field"""
        data = {}
        serializer = ForgetPasswordSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
    
    @patch('user.utils.email_service.EmailService.send_password_reset_email')
    def test_serializer_save_method(self, mock_send_email):
        """Test serializer save method"""
        mock_send_email.return_value = True
        
        data = {"email": "test@example.com"}
        serializer = ForgetPasswordSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        result = serializer.save()
        
        # Check that email was called
        mock_send_email.assert_called_once()
        
        # Check that user was updated with reset code
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.password_reset_code)
        self.assertIsNotNone(self.user.password_reset_code_expires_at)
        
        # Check return value
        self.assertTrue(result)


class PasswordResetConfirmSerializerTestCase(TestCase):
    """Test PasswordResetConfirmSerializer unit functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="test@example.com",
            full_name="Test User",
            password="TestPass123!"
        )
        # Set up password reset code
        self.user.password_reset_code = "123456"
        self.user.password_reset_code_expires_at = timezone.now() + timedelta(minutes=10)
        self.user.save()
    
    def test_serializer_valid_data(self):
        """Test serializer with valid data"""
        data = {
            "email": "test@example.com",
            "verification_code": "123456",
            "new_password": "NewPass123!",
            "confirm_new_password": "NewPass123!"
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
    
    def test_serializer_invalid_email(self):
        """Test serializer with invalid email"""
        data = {
            "email": "nonexistent@example.com",
            "verification_code": "123456",
            "new_password": "NewPass123!",
            "confirm_new_password": "NewPass123!"
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
    
    def test_serializer_invalid_verification_code(self):
        """Test serializer with invalid verification code"""
        data = {
            "email": "test@example.com",
            "verification_code": "wrong",
            "new_password": "NewPass123!",
            "confirm_new_password": "NewPass123!"
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("verification_code", serializer.errors)
    
    def test_serializer_expired_verification_code(self):
        """Test serializer with expired verification code"""
        # Make the code expired
        self.user.password_reset_code_expires_at = timezone.now() - timedelta(minutes=1)
        self.user.save()
        
        data = {
            "email": "test@example.com",
            "verification_code": "123456",
            "new_password": "NewPass123!",
            "confirm_new_password": "NewPass123!"
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("verification_code", serializer.errors)
    
    def test_serializer_password_mismatch(self):
        """Test serializer with password mismatch"""
        data = {
            "email": "test@example.com",
            "verification_code": "123456",
            "new_password": "NewPass123!",
            "confirm_new_password": "DifferentPass123!"
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("confirm_new_password", serializer.errors)
    
    def test_serializer_weak_password(self):
        """Test serializer with weak password"""
        data = {
            "email": "test@example.com",
            "verification_code": "123456",
            "new_password": "weak",
            "confirm_new_password": "weak"
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)
    
    @patch('user.utils.email_service.EmailService.send_password_reset_confirmation')
    def test_serializer_save_method(self, mock_send_confirmation):
        """Test serializer save method"""
        mock_send_confirmation.return_value = True
        old_password = self.user.password
        
        data = {
            "email": "test@example.com",
            "verification_code": "123456",
            "new_password": "NewPass123!",
            "confirm_new_password": "NewPass123!"
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        result = serializer.save()
        
        # Check that confirmation email was sent
        mock_send_confirmation.assert_called_once()
        
        # Check that user password was changed
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, old_password)
        
        # Check that reset code was cleared
        self.assertIsNone(self.user.password_reset_code)
        self.assertIsNone(self.user.password_reset_code_expires_at)
        
        # Check that user can login with new password
        self.assertTrue(self.user.check_password("NewPass123!"))
        
        # Check return value
        self.assertTrue(result)


class ResendPasswordResetSerializerTestCase(TestCase):
    """Test ResendPasswordResetSerializer unit functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="test@example.com",
            full_name="Test User",
            password="TestPass123!"
        )
    
    def test_serializer_valid_data_no_existing_code(self):
        """Test serializer with valid email and no existing code"""
        data = {"email": "test@example.com"}
        serializer = ResendPasswordResetSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
    
    def test_serializer_valid_data_expired_code(self):
        """Test serializer with valid email and expired code"""
        # Set expired code
        self.user.password_reset_code = "123456"
        self.user.password_reset_code_expires_at = timezone.now() - timedelta(minutes=1)
        self.user.save()
        
        data = {"email": "test@example.com"}
        serializer = ResendPasswordResetSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
    
    def test_serializer_invalid_recent_code(self):
        """Test serializer with recent valid code (rate limiting)"""
        # Set recent code
        self.user.password_reset_code = "123456"
        self.user.password_reset_code_expires_at = timezone.now() + timedelta(minutes=10)
        self.user.save()
        
        data = {"email": "test@example.com"}
        serializer = ResendPasswordResetSerializer(data=data)
        
        # Should be invalid due to rate limiting
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
    
    def test_serializer_invalid_email(self):
        """Test serializer with non-existent email"""
        data = {"email": "nonexistent@example.com"}
        serializer = ResendPasswordResetSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
    
    @patch('user.utils.email_service.EmailService.send_password_reset_email')
    def test_serializer_save_method(self, mock_send_email):
        """Test serializer save method"""
        mock_send_email.return_value = True
        
        data = {"email": "test@example.com"}
        serializer = ResendPasswordResetSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        result = serializer.save()
        
        # Check that email was sent
        mock_send_email.assert_called_once()
        
        # Check that user was updated with new reset code
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.password_reset_code)
        self.assertIsNotNone(self.user.password_reset_code_expires_at)
        
        # Check return value
        self.assertTrue(result)


class EmailServiceTestCase(TestCase):
    """Test EmailService unit functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="test@example.com",
            full_name="Test User",
            password="TestPass123!"
        )
    
    @patch('django.core.mail.send_mail')
    def test_send_password_reset_email_success(self, mock_send_mail):
        """Test successful password reset email sending"""
        mock_send_mail.return_value = True
        
        result = EmailService.send_password_reset_email(self.user, "123456")
        
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        
        # Check email content
        call_args = mock_send_mail.call_args
        self.assertIn("Password Reset", call_args[1]['subject'])
        self.assertIn("123456", call_args[1]['message'])
        self.assertEqual(call_args[1]['recipient_list'], [self.user.email])
    
    @patch('django.core.mail.send_mail')
    def test_send_password_reset_email_failure(self, mock_send_mail):
        """Test failed password reset email sending"""
        mock_send_mail.side_effect = Exception("SMTP Error")
        
        result = EmailService.send_password_reset_email(self.user, "123456")
        
        self.assertFalse(result)
        mock_send_mail.assert_called_once()
    
    @patch('django.core.mail.send_mail')
    def test_send_password_reset_confirmation_success(self, mock_send_confirmation):
        """Test successful password reset confirmation email"""
        mock_send_confirmation.return_value = True
        
        result = EmailService.send_password_reset_confirmation(self.user)
        
        self.assertTrue(result)
        mock_send_confirmation.assert_called_once()
        
        # Check email content
        call_args = mock_send_confirmation.call_args
        self.assertIn("Password Reset Successful", call_args[1]['subject'])
        self.assertEqual(call_args[1]['recipient_list'], [self.user.email])
    
    @patch('django.core.mail.send_mail')
    def test_send_password_reset_confirmation_failure(self, mock_send_confirmation):
        """Test failed password reset confirmation email"""
        mock_send_confirmation.side_effect = Exception("SMTP Error")
        
        result = EmailService.send_password_reset_confirmation(self.user)
        
        self.assertFalse(result)
        mock_send_confirmation.assert_called_once()


if __name__ == '__main__':
    unittest.main()
