"""
URL patterns for notifications
"""
from django.urls import path
from notifications.views import (
    GetUserNotificationsView, MarkNotificationAsReadView, MarkAllNotificationsAsReadView,
    GetNotificationPreferencesView, UpdateNotificationPreferencesView,
    AdminSendBroadcastNotificationView, AdminListBroadcastNotificationsView
)

app_name = 'notifications'

urlpatterns = [
    # User notification endpoints
    path('', GetUserNotificationsView.as_view(), name='get_notifications'),
    path('<uuid:notification_id>/read/', MarkNotificationAsReadView.as_view(), name='mark_notification_read'),
    path('read-all/', MarkAllNotificationsAsReadView.as_view(), name='mark_all_read'),
    
    # User preference endpoints
    path('preferences/', GetNotificationPreferencesView.as_view(), name='get_preferences'),
    path('preferences/update/', UpdateNotificationPreferencesView.as_view(), name='update_preferences'),
    
    # Admin broadcast notification endpoints
    path('workspaces/<uuid:workspace_id>/broadcast/', AdminSendBroadcastNotificationView.as_view(), name='send_broadcast'),
    path('workspaces/<uuid:workspace_id>/broadcast-list/', AdminListBroadcastNotificationsView.as_view(), name='list_broadcast'),
]
