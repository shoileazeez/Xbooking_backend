from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch

from user.models import User
from workspace.models import Workspace, Branch, Space
from booking.models import Booking


class TestOrderConfirmationEmailTask(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(full_name="Order User", email="orderuser@example.com", is_active=True)
        self.user.set_password("Pass12345!")
        self.user.save()
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}

        self.workspace = Workspace.objects.create(
            name="Order Workspace",
            admin=self.user,
            email="ow@example.com",
            city="City",
            country="CO"
        )
        self.branch = Branch.objects.create(
            workspace=self.workspace,
            name="Branch",
            email="b@example.com",
            address="Addr",
            city="City",
            country="CO"
        )
        self.space = Space.objects.create(
            branch=self.branch,
            name="Space",
            space_type="meeting_room",
            capacity=2,
            price_per_hour=10,
            daily_rate=50,
            monthly_rate=1000
        )

        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        check_in = now + timedelta(hours=1)
        check_out = check_in + timedelta(hours=2)

        self.booking = Booking.objects.create(
            workspace=self.workspace,
            space=self.space,
            user=self.user,
            booking_type='daily',
            booking_date=now.date(),
            start_time=check_in.time(),
            end_time=check_out.time(),
            check_in=check_in,
            check_out=check_out,
            number_of_guests=1,
            base_price=50,
            discount_amount=0,
            tax_amount=0,
            total_price=50,
            status='pending'
        )

    def test_create_order_queues_confirmation_email_task(self):
        url = reverse('payment:create_order')
        payload = {"booking_ids": [str(self.booking.id)]}
        with patch('qr_code.tasks.send_order_confirmation_email.delay') as mock_delay:
            response = self.client.post(url, payload, format='json', **self.auth_headers)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(mock_delay.called)

