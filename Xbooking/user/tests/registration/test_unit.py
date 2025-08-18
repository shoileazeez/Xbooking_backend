from django.test import TestCase
from django.core.exceptions import ValidationError
from user.models import User
from user.serializers import UserSerializers
from django.contrib.auth.hashers import check_password
import uuid


class UserRegistrationUnitTests(TestCase):
    """Unit tests for user registration components"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_user_data = {
            'full_name': 'John Doe',
            'email': 'john.doe@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!'
        }
        
        self.invalid_user_data = {
            'full_name': 'Jane Doe',
            'email': 'invalid-email',
            'password': 'weak',
            'confirm_password': 'different'
        }
    
    def test_user_model_creation(self):
        """Test User model creation with valid data"""
        user = User.objects.create(
            full_name='Test User',
            email='test@example.com',
            password='hashed_password',
            is_active=True
        )
        
        self.assertEqual(user.full_name, 'Test User')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.is_active)
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertIsNotNone(user.date_joined)
    
    def test_user_model_str_method(self):
        """Test User model __str__ method"""
        user = User.objects.create(
            full_name='Test User',
            email='test@example.com',
            password='hashed_password'
        )
        
        self.assertEqual(str(user), 'Test User')
    
    def test_user_set_password_method(self):
        """Test User model set_password method"""
        user = User.objects.create(
            full_name='Test User',
            email='test@example.com',
            password='temp_password'
        )
        
        raw_password = 'MySecurePassword123!'
        user.set_password(raw_password)
        
        # Check that password is hashed
        self.assertNotEqual(user.password, raw_password)
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        
        # Check that password can be verified
        self.assertTrue(user.check_password(raw_password))
        self.assertFalse(user.check_password('wrong_password'))
    
    def test_user_check_password_method(self):
        """Test User model check_password method"""
        user = User.objects.create(
            full_name='Test User',
            email='test@example.com',
            password='temp_password'
        )
        
        raw_password = 'TestPassword123!'
        user.set_password(raw_password)
        user.save()
        
        # Test correct password
        self.assertTrue(user.check_password(raw_password))
        
        # Test incorrect password
        self.assertFalse(user.check_password('wrong_password'))
        self.assertFalse(user.check_password(''))
    
    def test_user_email_uniqueness(self):
        """Test that email field is unique"""
        # Create first user
        User.objects.create(
            full_name='User One',
            email='unique@example.com',
            password='password123'
        )
        
        # Try to create second user with same email
        with self.assertRaises(Exception):  # This should raise an IntegrityError
            User.objects.create(
                full_name='User Two',
                email='unique@example.com',
                password='password456'
            )
    
    def test_serializer_valid_data(self):
        """Test UserSerializers with valid data"""
        serializer = UserSerializers(data=self.valid_user_data)
        self.assertTrue(serializer.is_valid())
        
        # Test that serializer can create user
        user = serializer.save()
        self.assertEqual(user.full_name, 'John Doe')
        self.assertEqual(user.email, 'john.doe@example.com')
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.avatar_url)
    
    def test_serializer_invalid_email(self):
        """Test UserSerializers with invalid email"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['email'] = 'invalid-email'
        
        serializer = UserSerializers(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_serializer_password_mismatch(self):
        """Test UserSerializers with password mismatch"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['confirm_password'] = 'DifferentPassword123!'
        
        serializer = UserSerializers(data=invalid_data)
        self.assertFalse(serializer.is_valid())
    
    def test_serializer_duplicate_email(self):
        """Test UserSerializers with duplicate email"""
        # Create first user
        User.objects.create(
            full_name='Existing User',
            email='john.doe@example.com',
            password='password123'
        )
        
        # Try to create second user with same email
        serializer = UserSerializers(data=self.valid_user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_serializer_avatar_url_generation(self):
        """Test that avatar URL is generated correctly"""
        serializer = UserSerializers(data=self.valid_user_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertIsNotNone(user.avatar_url)
        self.assertIn('dicebear.com', user.avatar_url)
        self.assertIn('john.doe%40example.com', user.avatar_url)
    
    def test_serializer_password_hashing(self):
        """Test that password is properly hashed during serialization"""
        serializer = UserSerializers(data=self.valid_user_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        
        # Password should be hashed
        self.assertNotEqual(user.password, 'SecurePass123!')
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        
        # User should be able to authenticate with original password
        self.assertTrue(user.check_password('SecurePass123!'))
    
    def test_serializer_fields_inclusion(self):
        """Test that all required fields are included in serializer"""
        serializer = UserSerializers()
        expected_fields = ['id', 'full_name', 'email', 'password', 'confirm_password', 'is_active', 'avatar_url']
        
        for field in expected_fields:
            self.assertIn(field, serializer.fields)
    
    def test_serializer_read_only_fields(self):
        """Test that read-only fields are properly configured"""
        serializer = UserSerializers()
        
        # Check read-only fields
        self.assertTrue(serializer.fields['id'].read_only)
        self.assertTrue(serializer.fields['is_active'].read_only)
        self.assertTrue(serializer.fields['avatar_url'].read_only)
        
        # Check write-only fields
        self.assertTrue(serializer.fields['password'].write_only)
        self.assertTrue(serializer.fields['confirm_password'].write_only)
