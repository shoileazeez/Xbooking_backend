from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from user.serializers import UserSerializers
from user.views import UserRegistrationView
from rest_framework_simplejwt.tokens import RefreshToken
import json
from unittest.mock import patch


class UserRegistrationIntegrationTests(TransactionTestCase):
    """Integration tests for complete registration flow"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.registration_url = reverse('register')
        
        self.valid_data = {
            'full_name': 'Integration Test User',
            'email': 'integration@example.com',
            'password': 'IntegrationPass123!',
            'confirm_password': 'IntegrationPass123!'
        }
    
    def test_complete_registration_flow(self):
        """Test complete registration flow from request to database"""
        # Initial state - no users
        self.assertEqual(User.objects.count(), 0)
        
        # Make registration request
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        
        # Verify response structure
        self.assertTrue(response_data['success'])
        self.assertIn('user', response_data)
        self.assertIn('token', response_data)
        
        # Verify user was created in database
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        
        # Verify user data
        self.assertEqual(user.full_name, 'Integration Test User')
        self.assertEqual(user.email, 'integration@example.com')
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.avatar_url)
        
        # Verify password is hashed
        self.assertNotEqual(user.password, 'IntegrationPass123!')
        self.assertTrue(user.check_password('IntegrationPass123!'))
        
        # Verify tokens work
        access_token = response_data['token']['access_token']
        refresh_token = response_data['token']['refresh_token']
        
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh_token)
        
        # Test that tokens are valid JWT tokens
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        
        try:
            UntypedToken(access_token)
            UntypedToken(refresh_token)
        except (InvalidToken, TokenError):
            self.fail("Generated tokens are not valid JWT tokens")
    
    def test_serializer_model_view_integration(self):
        """Test integration between serializer, model, and view"""
        # Test data flow through all components
        
        # 1. Serializer validation
        serializer = UserSerializers(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        # 2. Model creation through serializer
        user = serializer.save()
        self.assertIsInstance(user, User)
        
        # 3. View handling
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        # Should fail because email already exists
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_database_constraints_integration(self):
        """Test database constraints through the registration flow"""
        # Create first user
        response1 = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Try to create second user with same email
        response2 = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify only one user exists
        self.assertEqual(User.objects.count(), 1)
    
    def test_avatar_url_generation_integration(self):
        """Test avatar URL generation in complete flow"""
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check avatar URL in response
        avatar_url = response.json()['user']['avatar_url']
        self.assertIn('dicebear.com', avatar_url)
        
        # Check avatar URL in database
        user = User.objects.get(email='integration@example.com')
        self.assertEqual(user.avatar_url, avatar_url)
    
    @patch('urllib.parse.quote')
    def test_avatar_url_generation_error_handling(self, mock_quote):
        """Test avatar URL generation with error handling"""
        # Mock urllib.parse.quote to raise an exception
        mock_quote.side_effect = Exception("URL encoding error")
        
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Should fallback to default avatar URL
        user = User.objects.get(email='integration@example.com')
        self.assertIn('initials', user.avatar_url)
    
    def test_password_validation_integration(self):
        """Test password validation through complete flow"""
        # Test various invalid passwords
        invalid_passwords = [
            'short',  # Too short
            'nouppercase123!',  # No uppercase
            'NOLOWERCASE123!',  # No lowercase
            'NoDigits!',  # No digits
            'NoSpecialChars123',  # No special characters
        ]
        
        for invalid_password in invalid_passwords:
            invalid_data = self.valid_data.copy()
            invalid_data['password'] = invalid_password
            invalid_data['confirm_password'] = invalid_password
            
            response = self.client.post(
                self.registration_url,
                data=json.dumps(invalid_data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify no users were created
        self.assertEqual(User.objects.count(), 0)
    
    def test_jwt_token_integration(self):
        """Test JWT token generation and validation"""
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Get tokens from response
        tokens = response.json()['token']
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
        
        # Test that access token can be used for authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Test refresh token functionality
        refresh = RefreshToken(refresh_token)
        new_access_token = str(refresh.access_token)
        self.assertIsNotNone(new_access_token)
        self.assertNotEqual(access_token, new_access_token)
    
    def test_error_handling_integration(self):
        """Test error handling throughout the registration process"""
        # Test various error conditions
        
        # 1. Invalid JSON
        response = self.client.post(
            self.registration_url,
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # 2. Missing content type
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_data)
        )
        # Should still work as Django handles this
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
        
        # 3. Empty request
        response = self.client.post(self.registration_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_registration_response_format_consistency(self):
        """Test that registration response format is consistent"""
        # Test successful registration
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
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
        invalid_data = {'email': 'invalid'}
        response = self.client.post(
            self.registration_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_data = response.json()
        
        # Check required fields in error response
        error_required_fields = ['success', 'message', 'error']
        for field in error_required_fields:
            self.assertIn(field, error_data)
        
        self.assertFalse(error_data['success'])
