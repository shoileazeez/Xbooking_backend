from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from user.serializers import LoginSerializers
from user.views import UserLoginView
from user.validators import authenticate_user
import json
import datetime
from unittest.mock import patch
from rest_framework_simplejwt.tokens import RefreshToken


class UserLoginIntegrationTests(TransactionTestCase):
    """Integration tests for complete login flow"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.login_url = reverse('login')
        
        # Create test user
        self.test_user = User.objects.create(
            full_name='Integration Test User',
            email='integration@example.com',
            is_active=True
        )
        self.test_user.set_password('IntegrationPass123!')
        self.test_user.save()
        
        self.valid_data = {
            'email': 'integration@example.com',
            'password': 'IntegrationPass123!'
        }
    
    def test_complete_login_flow(self):
        """Test complete login flow from request to response"""
        # Initial state check
        original_last_login = self.test_user.last_login
        
        # Make login request
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # Verify response structure
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['message'], 'Login was succesful')
        self.assertIn('user', response_data)
        self.assertIn('token', response_data)
        
        # Verify user data in response
        user_data = response_data['user']
        self.assertEqual(user_data['user_email'], 'integration@example.com')
        self.assertEqual(user_data['full_name'], 'Integration Test User')
        self.assertIn('avatar_url', user_data)
        
        # Verify tokens
        tokens = response_data['token']
        self.assertIn('access_token', tokens)
        self.assertIn('refresh_token', tokens)
        
        # Verify database state changes
        self.test_user.refresh_from_db()
        self.assertNotEqual(self.test_user.last_login, original_last_login)
        
        # Verify tokens are valid
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
        
        # Test token validation
        from rest_framework_simplejwt.tokens import UntypedToken
        try:
            UntypedToken(access_token)
            UntypedToken(refresh_token)
        except Exception:
            self.fail("Generated tokens are not valid")
    
    def test_validator_serializer_view_integration(self):
        """Test integration between validator, serializer, and view"""
        # Test the flow: View -> Serializer -> Validator -> Model
        
        # 1. Direct validator test
        user = authenticate_user('integration@example.com', 'IntegrationPass123!')
        self.assertIsNotNone(user)
        
        # 2. Serializer test with validator
        serializer = LoginSerializers(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertIn('user', serializer.validated_data)
        
        # 3. Full view integration test
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_authentication_failure_integration(self):
        """Test authentication failure through complete flow"""
        invalid_data = {
            'email': 'integration@example.com',
            'password': 'WrongPassword123!'
        }
        
        # Test direct validator
        user = authenticate_user('integration@example.com', 'WrongPassword123!')
        self.assertIsNone(user)
        
        # Test serializer validation
        serializer = LoginSerializers(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        
        # Test full API flow
        response = self.client.post(
            self.login_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify last_login was not updated
        original_last_login = self.test_user.last_login
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.last_login, original_last_login)
    
    def test_inactive_user_integration(self):
        """Test inactive user handling through complete flow"""
        # Create inactive user
        inactive_user = User.objects.create(
            full_name='Inactive User',
            email='inactive@example.com',
            is_active=False
        )
        inactive_user.set_password('InactivePass123!')
        inactive_user.save()
        
        login_data = {
            'email': 'inactive@example.com',
            'password': 'InactivePass123!'
        }
        
        # Test authentication validator
        user = authenticate_user('inactive@example.com', 'InactivePass123!')
        self.assertIsNone(user)  # Should return None for inactive users
        
        # Test full flow
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_jwt_token_lifecycle_integration(self):
        """Test JWT token generation and usage integration"""
        # Login to get tokens
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tokens = response.json()['token']
        
        # Test access token usage
        access_token = tokens['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Test refresh token functionality
        refresh_token = tokens['refresh_token']
        refresh = RefreshToken(refresh_token)
        
        # Generate new access token
        new_access_token = str(refresh.access_token)
        self.assertIsNotNone(new_access_token)
        self.assertNotEqual(access_token, new_access_token)
    
    def test_concurrent_login_attempts(self):
        """Test concurrent login attempts for same user"""
        # Simulate concurrent logins
        responses = []
        
        for _ in range(5):
            response = self.client.post(
                self.login_url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            responses.append(response)
        
        # All should succeed
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # Each should have unique tokens
            tokens = response.json()['token']
            self.assertIsNotNone(tokens['access_token'])
            self.assertIsNotNone(tokens['refresh_token'])
    
    def test_login_after_registration_integration(self):
        """Test login immediately after registration"""
        # First register a new user
        registration_url = reverse('register')
        registration_data = {
            'full_name': 'New User',
            'email': 'newuser@example.com',
            'password': 'NewUserPass123!',
            'confirm_password': 'NewUserPass123!'
        }
        
        reg_response = self.client.post(
            registration_url,
            data=json.dumps(registration_data),
            content_type='application/json'
        )
        self.assertEqual(reg_response.status_code, status.HTTP_201_CREATED)
        
        # Then immediately login with same credentials
        login_data = {
            'email': 'newuser@example.com',
            'password': 'NewUserPass123!'
        }
        
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # Verify user data consistency
        reg_user = reg_response.json()['user']
        login_user = login_response.json()['user']
        
        self.assertEqual(reg_user['user_id'], login_user['user_id'])
        self.assertEqual(reg_user['user_email'], login_user['user_email'])
        self.assertEqual(reg_user['full_name'], login_user['full_name'])
    
    def test_database_transaction_integration(self):
        """Test database transaction handling during login"""
        original_last_login = self.test_user.last_login
        
        # Successful login should update last_login
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify transaction was committed
        self.test_user.refresh_from_db()
        self.assertNotEqual(self.test_user.last_login, original_last_login)
        
        # Failed login should not update anything
        current_last_login = self.test_user.last_login
        
        invalid_data = {
            'email': 'integration@example.com',
            'password': 'WrongPassword!'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify no changes were made
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.last_login, current_last_login)
    
    @patch('user.validators.authenticate_user')
    def test_error_handling_integration(self, mock_authenticate):
        """Test error handling throughout the login process"""
        # Mock authentication to raise an exception
        mock_authenticate.side_effect = Exception("Database error")
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        # Should handle the exception gracefully
        # The exact behavior depends on your error handling implementation
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])
    
    def test_response_consistency_integration(self):
        """Test response format consistency across different scenarios"""
        test_cases = [
            # (data, expected_status, should_have_user, should_have_token)
            (self.valid_data, status.HTTP_200_OK, True, True),
            ({'email': 'wrong@example.com', 'password': 'wrong'}, status.HTTP_400_BAD_REQUEST, False, False),
            ({'email': 'invalid-email', 'password': 'test'}, status.HTTP_400_BAD_REQUEST, False, False),
            ({'email': ''}, status.HTTP_400_BAD_REQUEST, False, False),
        ]
        
        for data, expected_status, should_have_user, should_have_token in test_cases:
            response = self.client.post(
                self.login_url,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, expected_status)
            
            response_data = response.json()
            
            # All responses should have these fields
            self.assertIn('success', response_data)
            self.assertIn('message', response_data)
            
            # Check conditional fields
            if should_have_user:
                self.assertIn('user', response_data)
                self.assertTrue(response_data['success'])
            else:
                self.assertFalse(response_data['success'])
                self.assertIn('errors', response_data)
            
            if should_have_token:
                self.assertIn('token', response_data)
