"""
Bank URLs - Main routing
"""
from django.urls import path, include

app_name = 'bank'

urlpatterns = [
    # V1 API
    path('v1/', include('bank.urls_v1')),
]
