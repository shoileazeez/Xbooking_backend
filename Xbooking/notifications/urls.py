"""
URL patterns for notifications - Redirects to v1
"""
from django.urls import path, include

app_name = 'notifications'

urlpatterns = [
    path('', include('notifications.urls_v1')),
]
