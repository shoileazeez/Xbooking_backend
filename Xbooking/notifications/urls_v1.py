"""
Notifications V1 URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from notifications.views.v1 import (
    NotificationViewSet,
    NotificationPreferenceViewSet,
    BroadcastNotificationViewSet
)

app_name = 'notifications_v1'

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')  # Register at root
router.register(r'preferences', NotificationPreferenceViewSet, basename='preference')
router.register(r'broadcasts', BroadcastNotificationViewSet, basename='broadcast')

urlpatterns = [
    path('', include(router.urls)),
]
