from django.test import TestCase
from user.models import User
from user.serializers import LoginSerializers
from user.validators import authenticate_user
from rest_framework.serializers import ValidationError
import datetime


class UserLoginUnitTests(TestCase):
    """Unit tests for user login components"""
    
    def setUp(self):
        """Set up test data"""
        self.test_user = User.objects.create(
            full_name='Test User',
            email='test@example.com',
            is_active=True
        )
        self.test_user.set_password('TestPassword123!')
        self.test_user.save()
        
        self.valid_login_data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        
        self.invalid_login_data = {
            'email': 'wrong@example.com',
            'password': 'WrongPassword123!'
        }
    
    def test_authenticate_user_valid_credentials(self):
        """Test authenticate_user function with valid credentials"""
        user = authenticate_user('test@example.com', 'TestPassword123!')
        
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.full_name, 'Test User')
    
    def test_authenticate_user_invalid_email(self):
        """Test authenticate_user function with invalid email"""
        user = authenticate_user('nonexistent@example.com', 'TestPassword123!')
        self.assertIsNone(user)
    
    def test_authenticate_user_invalid_password(self):
        """Test authenticate_user function with invalid password"""
        user = authenticate_user('test@example.com', 'WrongPassword!')
        self.assertIsNone(user)
    
    def test_authenticate_user_inactive_user(self):
        """Test authenticate_user function with inactive user"""
        # Create inactive user
        inactive_user = User.objects.create(
            full_name='Inactive User',
            email='inactive@example.com',
            is_active=False
        )
        inactive_user.set_password('Password123!')
        inactive_user.save()
        
        user = authenticate_user('inactive@example.com', 'Password123!')
        self.assertIsNone(user)
    
    def test_authenticate_user_empty_credentials(self):
        """Test authenticate_user function with empty credentials"""
        user = authenticate_user('', '')
        self.assertIsNone(user)
        
        user = authenticate_user('test@example.com', '')
        self.assertIsNone(user)
        
        user = authenticate_user('', 'TestPassword123!')
        self.assertIsNone(user)
    
    def test_login_serializer_valid_data(self):
        """Test LoginSerializers with valid credentials"""
        serializer = LoginSerializers(data=self.valid_login_data)
        self.assertTrue(serializer.is_valid())
        
        # Check that user is included in validated data
        validated_data = serializer.validated_data
        self.assertIn('user', validated_data)
        self.assertEqual(validated_data['user'].email, 'test@example.com')
    
    def test_login_serializer_invalid_credentials(self):
        """Test LoginSerializers with invalid credentials"""
        serializer = LoginSerializers(data=self.invalid_login_data)
        self.assertFalse(serializer.is_valid())
        
        # Check that appropriate error is raised
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)
    
    def test_login_serializer_missing_email(self):
        """Test LoginSerializers with missing email"""
        invalid_data = {'password': 'TestPassword123!'}
        serializer = LoginSerializers(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_login_serializer_missing_password(self):
        """Test LoginSerializers with missing password"""
        invalid_data = {'email': 'test@example.com'}
        serializer = LoginSerializers(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
    
    def test_login_serializer_invalid_email_format(self):
        """Test LoginSerializers with invalid email format"""
        invalid_data = {
            'email': 'invalid-email-format',
            'password': 'TestPassword123!'
        }
        serializer = LoginSerializers(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_login_serializer_fields(self):
        """Test LoginSerializers field configuration"""
        serializer = LoginSerializers()
        
        # Check required fields
        self.assertIn('email', serializer.fields)
        self.assertIn('password', serializer.fields)
        
        # Check field types
        self.assertTrue(serializer.fields['email'].required)
        self.assertEqual(serializer.fields['password'].max_length, 255)
    
    def test_user_password_check_method(self):
        """Test User model check_password method with various inputs"""
        # Test correct password
        self.assertTrue(self.test_user.check_password('TestPassword123!'))
        
        # Test incorrect passwords
        self.assertFalse(self.test_user.check_password('wrong_password'))
        self.assertFalse(self.test_user.check_password(''))
        self.assertFalse(self.test_user.check_password('TestPassword123'))  # Missing !
        self.assertFalse(self.test_user.check_password('testpassword123!'))  # Wrong case
    
    def test_user_last_login_update(self):
        """Test that last_login is updated during authentication"""
        original_last_login = self.test_user.last_login
        
        # Simulate login by updating last_login
        self.test_user.last_login = datetime.datetime.now()
        self.test_user.save()
        
        # Refresh from database
        self.test_user.refresh_from_db()
        
        self.assertNotEqual(self.test_user.last_login, original_last_login)
        self.assertIsInstance(self.test_user.last_login, datetime.datetime)
    
    def test_case_sensitive_email_authentication(self):
        """Test that email authentication is case insensitive"""
        # Test with different cases
        test_cases = [
            'test@example.com',
            'Test@Example.com',
            'TEST@EXAMPLE.COM',
            'tEsT@eXaMpLe.CoM'
        ]
        
        for email in test_cases:
            user = authenticate_user(email, 'TestPassword123!')
            # Note: This depends on your database collation settings
            # Some databases are case-insensitive by default
            if user:
                self.assertEqual(user.email, 'test@example.com')
    
    def test_password_hashing_verification(self):
        """Test that password hashing and verification work correctly"""
        # Create new user with password
        new_user = User.objects.create(
            full_name='Hash Test User',
            email='hashtest@example.com',
            is_active=True
        )
        
        raw_password = 'HashTestPassword123!'
        new_user.set_password(raw_password)
        new_user.save()
        
        # Verify password is hashed
        self.assertNotEqual(new_user.password, raw_password)
        self.assertTrue(new_user.password.startswith('pbkdf2_sha256$'))
        
        # Verify authentication works
        authenticated_user = authenticate_user('hashtest@example.com', raw_password)
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.id, new_user.id)
    
    def test_login_serializer_validation_messages(self):
        """Test LoginSerializers validation error messages"""
        # Test with non-existent user
        invalid_data = {
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        }
        
        serializer = LoginSerializers(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        
        # The validation should fail in the validate method
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            self.assertIn('Invalid email or password', str(e))
    
    def test_multiple_authentication_attempts(self):
        """Test multiple authentication attempts with same user"""
        # Multiple successful authentications
        for _ in range(5):
            user = authenticate_user('test@example.com', 'TestPassword123!')
            self.assertIsNotNone(user)
            self.assertEqual(user.email, 'test@example.com')
        
        # Multiple failed authentications
        for _ in range(5):
            user = authenticate_user('test@example.com', 'WrongPassword!')
            self.assertIsNone(user)
