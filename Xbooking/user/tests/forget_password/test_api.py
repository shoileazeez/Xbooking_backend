"""
API Tests for Forget Password Endpoint
Tests the HTTP API endpoint functionality, request/response handling, and authentication
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch
import json
from user.models import VerificationCode
from django.core import mail
from django.conf import settings

User = get_user_model()


class ForgetPasswordAPITest(APITestCase):
    """API tests for forget password endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.url = reverse('forget-password')  # Assuming this is the URL name
        
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com",
            avatar_url="http://example.com/avatar.jpg"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
        self.valid_payload = {
            'email': 'john.doe@example.com'
        }
        
        self.invalid_payload = {
            'email': 'nonexistent@example.com'
        }
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_forget_password_post_valid_email(self, mock_send_email):
        """Test POST request with valid email"""
        mock_send_email.return_value = True
        
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertIn('message', response_data)
        self.assertIn('sent successfully', response_data['message'])
        
        # Verify verification code was created
        verification_code = VerificationCode.objects.filter(user=self.user).first()
        self.assertIsNotNone(verification_code)
        
    def test_forget_password_post_invalid_email(self):
        """Test POST request with non-existent email"""
        response = self.client.post(
            self.url,
            data=json.dumps(self.invalid_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
        
    def test_forget_password_post_empty_email(self):
        """Test POST request with empty email"""
        response = self.client.post(
            self.url,
            data=json.dumps({'email': ''}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
        
    def test_forget_password_post_invalid_email_format(self):
        """Test POST request with invalid email format"""
        response = self.client.post(
            self.url,
            data=json.dumps({'email': 'invalid-email'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
        
    def test_forget_password_post_no_email_field(self):
        """Test POST request without email field"""
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
        
    def test_forget_password_get_method_not_allowed(self):
        """Test that GET method is not allowed"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
    def test_forget_password_put_method_not_allowed(self):
        """Test that PUT method is not allowed"""
        response = self.client.put(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
    def test_forget_password_delete_method_not_allowed(self):
        """Test that DELETE method is not allowed"""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_forget_password_rate_limiting(self, mock_send_email):
        """Test rate limiting functionality via API"""
        mock_send_email.return_value = True
        
        # First request should succeed
        response1 = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Second request should fail due to rate limiting
        response2 = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response2.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_forget_password_email_service_failure(self, mock_send_email):
        """Test API response when email service fails"""
        mock_send_email.return_value = False
        
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('message', response_data)
        
    def test_forget_password_malformed_json(self):
        """Test API response with malformed JSON"""
        response = self.client.post(
            self.url,
            data='{"email": "test@example.com"',  # Missing closing brace
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_forget_password_wrong_content_type(self):
        """Test API response with wrong content type"""
        response = self.client.post(
            self.url,
            data='email=john.doe@example.com',
            content_type='application/x-www-form-urlencoded'
        )
        
        # Should still work but verify behavior
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
        
    def test_forget_password_response_headers(self):
        """Test that response has correct headers"""
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_payload),
                content_type='application/json'
            )
            
            self.assertEqual(response['Content-Type'], 'application/json')
            
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_forget_password_response_structure(self, mock_send_email):
        """Test that response has the correct structure"""
        mock_send_email.return_value = True
        
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        
        response_data = response.json()
        
        # Check required fields in success response
        self.assertIn('success', response_data)
        self.assertIn('message', response_data)
        self.assertIsInstance(response_data['success'], bool)
        self.assertIsInstance(response_data['message'], str)
        
    def test_forget_password_case_insensitive_email(self):
        """Test that email lookup is case insensitive"""
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Test with uppercase email
            response = self.client.post(
                self.url,
                data=json.dumps({'email': 'JOHN.DOE@EXAMPLE.COM'}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
    def test_forget_password_unicode_email(self):
        """Test forget password with unicode characters in email"""
        # Create user with unicode email
        unicode_user = User.objects.create(
            full_name="José García",
            email="josé.garcía@example.com"
        )
        unicode_user.set_password("SecurePass123!")
        unicode_user.save()
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            response = self.client.post(
                self.url,
                data=json.dumps({'email': 'josé.garcía@example.com'}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class ForgetPasswordAPISecurityTest(APITestCase):
    """Security-focused API tests for forget password endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.url = reverse('forget-password')
        
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    def test_forget_password_sql_injection_attempt(self):
        """Test that SQL injection attempts are handled safely"""
        malicious_payload = {
            'email': "john.doe@example.com'; DROP TABLE user_user; --"
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(malicious_payload),
            content_type='application/json'
        )
        
        # Should return validation error, not cause SQL injection
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify user table still exists by querying it
        user_count = User.objects.count()
        self.assertEqual(user_count, 1)
        
    def test_forget_password_xss_attempt(self):
        """Test that XSS attempts are handled safely"""
        malicious_payload = {
            'email': "<script>alert('xss')</script>@example.com"
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(malicious_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        # Verify that the script tag is not reflected in the response
        response_str = json.dumps(response_data)
        self.assertNotIn('<script>', response_str)
        
    def test_forget_password_very_long_email(self):
        """Test handling of extremely long email addresses"""
        long_email = "a" * 1000 + "@example.com"
        
        response = self.client.post(
            self.url,
            data=json.dumps({'email': long_email}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_forget_password_multiple_rapid_requests(self):
        """Test multiple rapid requests to check for DoS protection"""
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            responses = []
            for i in range(10):  # Send 10 rapid requests
                response = self.client.post(
                    self.url,
                    data=json.dumps({'email': 'john.doe@example.com'}),
                    content_type='application/json'
                )
                responses.append(response.status_code)
                
            # Only first request should succeed, others should be rate limited
            success_count = sum(1 for status_code in responses if status_code == 200)
            self.assertEqual(success_count, 1)


class ForgetPasswordAPIPerformanceTest(APITestCase):
    """Performance tests for forget password API"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.url = reverse('forget-password')
        
        # Create multiple users for performance testing
        self.users = []
        for i in range(100):
            user = User.objects.create(
                full_name=f"User {i}",
                email=f"user{i}@example.com"
            )
            user.set_password("SecurePass123!")
            user.save()
            self.users.append(user)
            
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_forget_password_response_time(self, mock_send_email):
        """Test that response time is reasonable"""
        mock_send_email.return_value = True
        
        import time
        
        start_time = time.time()
        
        response = self.client.post(
            self.url,
            data=json.dumps({'email': 'user50@example.com'}),
            content_type='application/json'
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 2.0)  # Should respond within 2 seconds
        
    def test_forget_password_database_query_count(self):
        """Test that the number of database queries is optimized"""
        from django.test.utils import override_settings
        from django.db import connection
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Reset query log
            connection.queries = []
            
            response = self.client.post(
                self.url,
                data=json.dumps({'email': 'user50@example.com'}),
                content_type='application/json'
            )
            
            query_count = len(connection.queries)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertLess(query_count, 10)  # Should not exceed 10 queries
