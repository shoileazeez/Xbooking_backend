from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
import json


class UserRegistrationAPITests(TestCase):
    """API tests for user registration endpoint"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.registration_url = reverse('register')
        
        self.valid_registration_data = {
            'full_name': 'John Doe',
            'email': 'john.doe@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!'
        }
        
        self.invalid_registration_data = {
            'full_name': '',
            'email': 'invalid-email',
            'password': 'weak',
            'confirm_password': 'different'
        }
    
    def test_successful_registration(self):
        """Test successful user registration"""
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_registration_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check response structure
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['message'], 'Registration was succesful')
        
        # Check user data in response
        self.assertIn('user', response_data)
        user_data = response_data['user']
        self.assertEqual(user_data['user_email'], 'john.doe@example.com')
        self.assertEqual(user_data['full_name'], 'John Doe')
        self.assertIn('user_id', user_data)
        self.assertIn('avatar_url', user_data)
        
        # Check token data in response
        self.assertIn('token', response_data)
        token_data = response_data['token']
        self.assertIn('access_token', token_data)
        self.assertIn('refresh_token', token_data)
        
        # Verify user was created in database
        user = User.objects.get(email='john.doe@example.com')
        self.assertEqual(user.full_name, 'John Doe')
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password('SecurePass123!'))
    
    def test_registration_with_invalid_email(self):
        """Test registration with invalid email format"""
        invalid_data = self.valid_registration_data.copy()
        invalid_data['email'] = 'invalid-email-format'
        
        response = self.client.post(
            self.registration_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['message'], 'Registration Failed')
        self.assertIn('error', response_data)
    
    def test_registration_with_duplicate_email(self):
        """Test registration with already existing email"""
        # Create existing user
        User.objects.create(
            full_name='Existing User',
            email='john.doe@example.com',
            password='existing_password'
        )
        
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_registration_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    def test_registration_with_password_mismatch(self):
        """Test registration with password confirmation mismatch"""
        invalid_data = self.valid_registration_data.copy()
        invalid_data['confirm_password'] = 'DifferentPassword123!'
        
        response = self.client.post(
            self.registration_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
    
    def test_registration_with_weak_password(self):
        """Test registration with password that doesn't meet requirements"""
        invalid_data = self.valid_registration_data.copy()
        invalid_data['password'] = 'weak'
        invalid_data['confirm_password'] = 'weak'
        
        response = self.client.post(
            self.registration_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_registration_with_missing_fields(self):
        """Test registration with missing required fields"""
        incomplete_data = {
            'email': 'test@example.com'
            # Missing full_name, password, confirm_password
        }
        
        response = self.client.post(
            self.registration_url,
            data=json.dumps(incomplete_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    def test_registration_with_empty_data(self):
        """Test registration with empty request body"""
        response = self.client.post(
            self.registration_url,
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_registration_content_type_json(self):
        """Test that registration endpoint accepts JSON content type"""
        response = self.client.post(
            self.registration_url,
            data=self.valid_registration_data,  # form data instead of JSON
        )
        
        # Should still work with form data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_registration_method_not_allowed(self):
        """Test that only POST method is allowed for registration"""
        # Test GET method
        response = self.client.get(self.registration_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test PUT method
        response = self.client.put(
            self.registration_url,
            data=json.dumps(self.valid_registration_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test DELETE method
        response = self.client.delete(self.registration_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_avatar_url_generation(self):
        """Test that avatar URL is generated and included in response"""
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_registration_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        response_data = response.json()
        avatar_url = response_data['user']['avatar_url']
        
        self.assertIsNotNone(avatar_url)
        self.assertIn('dicebear.com', avatar_url)
        self.assertIn('john.doe%40example.com', avatar_url)
    
    def test_password_not_in_response(self):
        """Test that password is not included in registration response"""
        response = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_registration_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        response_data = response.json()
        user_data = response_data['user']
        
        # Password should not be in response
        self.assertNotIn('password', user_data)
        self.assertNotIn('confirm_password', user_data)
    
    def test_multiple_registrations_different_emails(self):
        """Test that multiple users can register with different emails"""
        # First registration
        response1 = self.client.post(
            self.registration_url,
            data=json.dumps(self.valid_registration_data),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second registration with different email
        second_data = self.valid_registration_data.copy()
        second_data['email'] = 'jane.doe@example.com'
        second_data['full_name'] = 'Jane Doe'
        
        response2 = self.client.post(
            self.registration_url,
            data=json.dumps(second_data),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # Verify both users exist
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(User.objects.filter(email='john.doe@example.com').exists())
        self.assertTrue(User.objects.filter(email='jane.doe@example.com').exists())
