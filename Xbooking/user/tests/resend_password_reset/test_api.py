"""
API Tests for Resend Password Reset Endpoint
Tests the HTTP API endpoint functionality, request/response handling, and security
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
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ResendPasswordResetAPITest(APITestCase):
    """API tests for resend password reset endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.url = reverse('resend-password-reset')  # Assuming this is the URL name
        
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
    def test_resend_password_reset_post_valid_email(self, mock_send_email):
        """Test POST request with valid email and existing old code"""
        mock_send_email.return_value = True
        
        # Create an old verification code
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
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
        
        # Verify new verification code was created
        verification_codes = VerificationCode.objects.filter(user=self.user)
        self.assertEqual(verification_codes.count(), 1)
        
        new_code = verification_codes.first()
        self.assertNotEqual(new_code.code, "123456")  # Should be different
        
    def test_resend_password_reset_post_invalid_email(self):
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
        
    def test_resend_password_reset_no_existing_request(self):
        """Test POST request when no existing password reset request"""
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
        
    def test_resend_password_reset_too_recent_request(self):
        """Test POST request when recent request exists (within 5 minutes)"""
        # Create a recent verification code
        VerificationCode.objects.create(
            user=self.user,
            code="123456"
        )
        
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
        
    def test_resend_password_reset_post_empty_email(self):
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
        
    def test_resend_password_reset_post_invalid_email_format(self):
        """Test POST request with invalid email format"""
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        response = self.client.post(
            self.url,
            data=json.dumps({'email': 'invalid-email'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)
        
    def test_resend_password_reset_get_method_not_allowed(self):
        """Test that GET method is not allowed"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
    def test_resend_password_reset_put_method_not_allowed(self):
        """Test that PUT method is not allowed"""
        response = self.client.put(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
    def test_resend_password_reset_delete_method_not_allowed(self):
        """Test that DELETE method is not allowed"""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_resend_password_reset_email_service_failure(self, mock_send_email):
        """Test API response when email service fails"""
        mock_send_email.return_value = False
        
        # Create an old verification code
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('message', response_data)
        
    def test_resend_password_reset_malformed_json(self):
        """Test API response with malformed JSON"""
        response = self.client.post(
            self.url,
            data='{"email": "test@example.com"',  # Missing closing brace
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_resend_password_reset_response_headers(self):
        """Test that response has correct headers"""
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_payload),
                content_type='application/json'
            )
            
            self.assertEqual(response['Content-Type'], 'application/json')
            
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_resend_password_reset_response_structure(self, mock_send_email):
        """Test that response has the correct structure"""
        mock_send_email.return_value = True
        
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
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
        
    def test_resend_password_reset_case_insensitive_email(self):
        """Test that email lookup is case insensitive"""
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Test with uppercase email
            response = self.client.post(
                self.url,
                data=json.dumps({'email': 'JOHN.DOE@EXAMPLE.COM'}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
    def test_resend_password_reset_timing_edge_cases(self):
        """Test timing edge cases for rate limiting"""
        # Test exactly 5 minutes ago (should work)
        edge_time = timezone.now() - timedelta(minutes=5, seconds=1)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=edge_time
        )
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class ResendPasswordResetAPISecurityTest(APITestCase):
    """Security-focused API tests for resend password reset endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.url = reverse('resend-password-reset')
        
        self.user = User.objects.create(
            full_name="John Doe",
            email="john.doe@example.com"
        )
        self.user.set_password("SecurePass123!")
        self.user.save()
        
    def test_resend_password_reset_sql_injection_attempt(self):
        """Test that SQL injection attempts are handled safely"""
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
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
        
        # Verify user table still exists
        user_count = User.objects.count()
        self.assertEqual(user_count, 1)
        
    def test_resend_password_reset_xss_attempt(self):
        """Test that XSS attempts are handled safely"""
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
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
        
    def test_resend_password_reset_very_long_email(self):
        """Test handling of extremely long email addresses"""
        long_email = "a" * 1000 + "@example.com"
        
        response = self.client.post(
            self.url,
            data=json.dumps({'email': long_email}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_resend_password_reset_rate_limiting_security(self):
        """Test that rate limiting prevents abuse"""
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # First request should succeed
            response1 = self.client.post(
                self.url,
                data=json.dumps({'email': self.user.email}),
                content_type='application/json'
            )
            self.assertEqual(response1.status_code, status.HTTP_200_OK)
            
            # Immediate second request should fail
            response2 = self.client.post(
                self.url,
                data=json.dumps({'email': self.user.email}),
                content_type='application/json'
            )
            self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
            
    def test_resend_password_reset_inactive_user_security(self):
        """Test that inactive users cannot request password resets"""
        self.user.is_active = False
        self.user.save()
        
        old_time = timezone.now() - timedelta(minutes=6)
        VerificationCode.objects.create(
            user=self.user,
            code="123456",
            created_at=old_time
        )
        
        response = self.client.post(
            self.url,
            data=json.dumps({'email': self.user.email}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_resend_password_reset_information_disclosure(self):
        """Test that the API doesn't disclose user existence"""
        # Request for non-existent user
        response = self.client.post(
            self.url,
            data=json.dumps({'email': 'nonexistent@example.com'}),
            content_type='application/json'
        )
        
        # Should not reveal whether user exists or not in error message
        response_data = response.json()
        error_message = json.dumps(response_data).lower()
        
        # Should not contain words that reveal user existence
        self.assertNotIn('user does not exist', error_message)
        self.assertNotIn('user not found', error_message)


class ResendPasswordResetAPIPerformanceTest(APITestCase):
    """Performance tests for resend password reset API"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.url = reverse('resend-password-reset')
        
        # Create multiple users for performance testing
        self.users = []
        for i in range(50):
            user = User.objects.create(
                full_name=f"User {i}",
                email=f"user{i}@example.com"
            )
            user.set_password("SecurePass123!")
            user.save()
            self.users.append(user)
            
            # Create old verification codes
            old_time = timezone.now() - timedelta(minutes=6)
            VerificationCode.objects.create(
                user=user,
                code=f"12345{i:02d}",
                created_at=old_time
            )
            
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_resend_password_reset_response_time(self, mock_send_email):
        """Test that response time is reasonable"""
        mock_send_email.return_value = True
        
        import time
        
        start_time = time.time()
        
        response = self.client.post(
            self.url,
            data=json.dumps({'email': 'user25@example.com'}),
            content_type='application/json'
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 2.0)  # Should respond within 2 seconds
        
    def test_resend_password_reset_database_query_count(self):
        """Test that the number of database queries is optimized"""
        from django.db import connection
        
        with patch('user.services.email_service.EmailService.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Reset query log
            connection.queries = []
            
            response = self.client.post(
                self.url,
                data=json.dumps({'email': 'user25@example.com'}),
                content_type='application/json'
            )
            
            query_count = len(connection.queries)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertLess(query_count, 15)  # Should not exceed 15 queries
            
    @patch('user.services.email_service.EmailService.send_password_reset_email')
    def test_resend_password_reset_concurrent_requests(self, mock_send_email):
        """Test handling of concurrent requests"""
        mock_send_email.return_value = True
        
        import threading
        import time
        
        responses = []
        
        def make_request():
            response = self.client.post(
                self.url,
                data=json.dumps({'email': 'user30@example.com'}),
                content_type='application/json'
            )
            responses.append(response.status_code)
            
        # Create multiple threads for concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Only one request should succeed due to rate limiting
        success_count = sum(1 for status_code in responses if status_code == 200)
        self.assertEqual(success_count, 1)
