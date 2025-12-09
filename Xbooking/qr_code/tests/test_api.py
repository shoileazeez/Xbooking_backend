from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from datetime import timedelta

from user.models import User
from workspace.models import Workspace, Branch, Space
from booking.models import Booking
from payment.models import Order
from qr_code.models import OrderQRCode, BookingQRCode


class TestQRCodeAPI(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(full_name="QR Tester", email="qrtester@example.com", is_active=True)
        self.user.set_password("TestPass123!")
        self.user.save()
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}

        self.workspace = Workspace.objects.create(
            name="Test Workspace",
            admin=self.user,
            email="ws@example.com",
            city="Test City",
            country="TC"
        )
        self.branch = Branch.objects.create(
            workspace=self.workspace,
            name="Main Branch",
            email="branch@example.com",
            address="123 Test St",
            city="Test City",
            country="TC"
        )
        self.space = Space.objects.create(
            branch=self.branch,
            name="Room A",
            space_type="meeting_room",
            capacity=4,
            price_per_hour=50,
            daily_rate=200,
            monthly_rate=3000
        )

        now = timezone.now()
        self.check_in = now + timedelta(hours=1)
        self.check_out = self.check_in + timedelta(hours=2)

        self.booking = Booking.objects.create(
            workspace=self.workspace,
            space=self.space,
            user=self.user,
            booking_type='daily',
            booking_date=now.date(),
            start_time=self.check_in.time(),
            end_time=self.check_out.time(),
            check_in=self.check_in,
            check_out=self.check_out,
            number_of_guests=1,
            base_price=200,
            discount_amount=0,
            tax_amount=0,
            total_price=200,
            status='confirmed'
        )

        self.order = Order.objects.create(
            workspace=self.workspace,
            user=self.user,
            subtotal=200,
            discount_amount=0,
            tax_amount=0,
            total_amount=200,
            status='paid',
            payment_method='paystack'
        )
        self.order.bookings.add(self.booking)

    def test_generate_order_qr_code_triggers_task(self):
        url = reverse('qr_code:generate_qr_code', kwargs={'order_id': self.order.id})
        with patch('qr_code.tasks.generate_qr_code_for_order.delay') as mock_delay:
            response = self.client.post(url, **self.auth_headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_delay.assert_called_once_with(str(self.order.id))

    def test_get_order_qr_code_returns_data(self):
        qr = OrderQRCode.objects.create(
            order=self.order,
            qr_code_data="https://example.com/verify/ORD-TEST",
            verification_code="ORD-TEST-CODE",
            status='generated',
            qr_code_image_url="https://res.cloudinary.com/demo/image/upload/v1/xbooking/ord_test.png",
            appwrite_file_id="xbooking/ord_test"
        )

        url = reverse('qr_code:get_qr_code', kwargs={'order_id': self.order.id})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get('verification_code'), qr.verification_code)
        self.assertEqual(data.get('qr_code_url'), qr.qr_code_image_url)
        self.assertIn('status', data)

    def test_get_booking_qr_code_returns_data(self):
        bqr = BookingQRCode.objects.create(
            booking=self.booking,
            order=self.order,
            qr_code_data="https://example.com/verify-booking/BKG-TEST",
            verification_code="BKG-TEST-CODE",
            status='generated',
            qr_code_image_url="https://res.cloudinary.com/demo/image/upload/v1/xbooking/bkg_test.png",
            appwrite_file_id="xbooking/bkg_test"
        )

        url = reverse('qr_code:get_booking_qr_code', kwargs={'booking_id': self.booking.id})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get('verification_code'), bqr.verification_code)
        self.assertEqual(data.get('qr_code_url'), bqr.qr_code_image_url)
        self.assertIn('space_name', data)

    def test_generate_requires_auth(self):
        url = reverse('qr_code:generate_qr_code', kwargs={'order_id': self.order.id})
        response = self.client.post(url)  # no auth headers
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
