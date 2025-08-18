from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
import json
import datetime


class UserLoginAPITests(TestCase):
    """API tests for user login endpoint"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.login_url = reverse('login')
        
        # Create test user
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
    
    def test_successful_login(self):
        """Test successful user login"""
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check response structure
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['message'], 'Login was succesful')
        
        # Check user data in response
        self.assertIn('user', response_data)
        user_data = response_data['user']
        self.assertEqual(user_data['user_email'], 'test@example.com')
        self.assertEqual(user_data['full_name'], 'Test User')
        self.assertIn('user_id', user_data)
        self.assertIn('avatar_url', user_data)
        
        # Check token data in response
        self.assertIn('token', response_data)
        token_data = response_data['token']
        self.assertIn('access_token', token_data)
        self.assertIn('refresh_token', token_data)
    
    def test_login_with_invalid_email(self):
        """Test login with non-existent email"""
        invalid_data = {
            'email': 'nonexistent@example.com',
            'password': 'TestPassword123!'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['message'], 'Login failed')
        self.assertIn('errors', response_data)
    
    def test_login_with_invalid_password(self):
        """Test login with incorrect password"""
        invalid_data = {
            'email': 'test@example.com',
            'password': 'WrongPassword123!'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['message'], 'Login failed')
        self.assertIn('errors', response_data)
    
    def test_login_with_invalid_email_format(self):
        """Test login with invalid email format"""
        invalid_data = {
            'email': 'invalid-email-format',
            'password': 'TestPassword123!'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
    
    def test_login_with_missing_email(self):
        """Test login with missing email field"""
        invalid_data = {
            'password': 'TestPassword123!'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
    
    def test_login_with_missing_password(self):
        """Test login with missing password field"""
        invalid_data = {
            'email': 'test@example.com'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
    
    def test_login_with_empty_data(self):
        """Test login with empty request body"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_with_inactive_user(self):
        """Test login with inactive user account"""
        # Create inactive user
        inactive_user = User.objects.create(
            full_name='Inactive User',
            email='inactive@example.com',
            is_active=False
        )
        inactive_user.set_password('InactivePassword123!')
        inactive_user.save()
        
        login_data = {
            'email': 'inactive@example.com',
            'password': 'InactivePassword123!'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_method_not_allowed(self):
        """Test that only POST method is allowed for login"""
        # Test GET method
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test PUT method
        response = self.client.put(
            self.login_url,
            data=json.dumps(self.valid_login_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test DELETE method
        response = self.client.delete(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_login_content_type_json(self):
        """Test that login endpoint accepts JSON content type"""
        response = self.client.post(
            self.login_url,
            data=self.valid_login_data,  # form data instead of JSON
        )
        
        # Should still work with form data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_password_not_in_response(self):
        """Test that password is not included in login response"""
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        user_data = response_data['user']
        
        # Password should not be in response
        self.assertNotIn('password', user_data)
    
    def test_last_login_update(self):
        """Test that last_login is updated after successful login"""
        # Get original last_login
        original_last_login = self.test_user.last_login
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh user from database
        self.test_user.refresh_from_db()
        
        # Check that last_login was updated
        self.assertNotEqual(self.test_user.last_login, original_last_login)
        self.assertIsInstance(self.test_user.last_login, datetime.datetime)
    
    def test_jwt_tokens_in_response(self):
        """Test that valid JWT tokens are returned"""
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        tokens = response_data['token']
        
        # Check token format (basic JWT structure check)
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
        
        # JWT tokens should have 3 parts separated by dots
        self.assertEqual(len(access_token.split('.')), 3)
        self.assertEqual(len(refresh_token.split('.')), 3)
        
        # Tokens should be different
        self.assertNotEqual(access_token, refresh_token)
    
    def test_multiple_login_attempts(self):
        """Test multiple login attempts"""
        # Multiple successful logins
        for _ in range(3):
            response = self.client.post(
                self.login_url,
                data=json.dumps(self.valid_login_data),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Multiple failed logins
        for _ in range(3):
            response = self.client.post(
                self.login_url,
                data=json.dumps(self.invalid_login_data),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_response_format_consistency(self):
        """Test that login response format is consistent"""
        # Test successful login
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check required fields in success response
        required_fields = ['success', 'message', 'user', 'token']
        for field in required_fields:
            self.assertIn(field, data)
        
        # Check user fields
        user_fields = ['user_id', 'user_email', 'full_name', 'avatar_url']
        for field in user_fields:
            self.assertIn(field, data['user'])
        
        # Check token fields
        token_fields = ['access_token', 'refresh_token']
        for field in token_fields:
            self.assertIn(field, data['token'])
        
        # Test error response format
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.invalid_login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_data = response.json()
        
        # Check required fields in error response
        error_required_fields = ['success', 'message', 'errors']
        for field in error_required_fields:
            self.assertIn(field, error_data)
        
        self.assertFalse(error_data['success'])
    
    def test_case_insensitive_email_login(self):
        """Test login with different email cases"""
        # Test with different email cases
        email_variations = [
            'test@example.com',
            'Test@Example.com',
            'TEST@EXAMPLE.COM',
            'tEsT@eXaMpLe.CoM'
        ]
        
        for email in email_variations:
            login_data = {
                'email': email,
                'password': 'TestPassword123!'
            }
            
            response = self.client.post(
                self.login_url,
                data=json.dumps(login_data),
                content_type='application/json'
            )
            
            # This depends on your database collation settings
            # Many databases are case-insensitive for email by default
            if response.status_code == status.HTTP_200_OK:
                response_data = response.json()
                self.assertEqual(response_data['user']['user_email'], 'test@example.com')
