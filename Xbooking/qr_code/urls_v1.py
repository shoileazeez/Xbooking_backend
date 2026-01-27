"""
QR Code URLs V1
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from qr_code.views.v1 import (
    OrderQRCodeViewSet,
    BookingQRCodeViewSet,
    AdminQRCodeViewSet
)

router = DefaultRouter()
router.register(r'orders', OrderQRCodeViewSet, basename='order-qr-codes')
router.register(r'bookings', BookingQRCodeViewSet, basename='booking-qr-codes')
router.register(r'admin', AdminQRCodeViewSet, basename='admin-qr-codes')

urlpatterns = [
    path('', include(router.urls)),
]
