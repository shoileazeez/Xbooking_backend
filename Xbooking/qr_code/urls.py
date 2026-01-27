"""
QR Code URLs - Main routing
"""
from django.urls import path, include

app_name = 'qr_code'

urlpatterns = [
    # V1 API
    path('v1/', include('qr_code.urls_v1')),
]
