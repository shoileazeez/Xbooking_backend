"""
QR Code Views V1
"""
from .qr_code import OrderQRCodeViewSet, BookingQRCodeViewSet
from .admin import AdminQRCodeViewSet


__all__ = [
    'OrderQRCodeViewSet',
    'BookingQRCodeViewSet',
    'AdminQRCodeViewSet',
]
