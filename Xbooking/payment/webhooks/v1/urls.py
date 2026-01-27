"""
Payment Webhook URLs V1
"""
from django.urls import path
from payment.webhooks.v1 import views

urlpatterns = [
    path('paystack/', views.paystack_webhook, name='paystack_webhook'),
    path('flutterwave/', views.flutterwave_webhook, name='flutterwave_webhook'),
]
