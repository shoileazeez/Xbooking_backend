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
from notifications.views.v1.push import (
    push_subscribe,
    push_unsubscribe,
    get_push_subscriptions,
    check_subscription_status
)
from notifications.views.v1.test_push import send_test_push

app_name = 'notifications_v1'

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')  # Register at root
router.register(r'preferences', NotificationPreferenceViewSet, basename='preference')
router.register(r'broadcasts', BroadcastNotificationViewSet, basename='broadcast')

urlpatterns = [
    # Push notification endpoints - must come before router.urls
    path('push-subscribe/', push_subscribe, name='push-subscribe'),
    path('push-unsubscribe/', push_unsubscribe, name='push-unsubscribe'),
    path('push-subscriptions/', get_push_subscriptions, name='push-subscriptions'),
    path('push-subscription-status/', check_subscription_status, name='push-subscription-status'),
    path('test-push/', send_test_push, name='test-push'),
    # Router URLs (catch-all)
    path('', include(router.urls)),
]
