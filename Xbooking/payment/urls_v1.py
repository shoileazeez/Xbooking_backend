"""
Payment V1 URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payment.views.v1 import OrderViewSet, PaymentViewSet, RefundViewSet
from payment.views.bank_api import BankListAPIView, BankResolveAPIView

app_name = 'payment_v1'

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'refunds', RefundViewSet, basename='refund')

urlpatterns = [
    path('', include(router.urls)),
    path('webhooks/', include('payment.webhooks.v1.urls')),
    path('banks/', BankListAPIView.as_view(), name='bank-list'),
    path('banks/resolve/', BankResolveAPIView.as_view(), name='bank-resolve'),
]
