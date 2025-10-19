"""
Admin configuration for notifications
"""
from django.contrib import admin
from notifications.models import Notification, NotificationPreference, BroadcastNotification, NotificationLog


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled', 'created_at']
    list_filter = ['email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'channel', 'title', 'is_read', 'is_sent', 'created_at']
    list_filter = ['notification_type', 'channel', 'is_read', 'is_sent', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    readonly_fields = ['created_at', 'updated_at', 'sent_at', 'read_at', 'clicked_at']


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['notification', 'status', 'attempt_number', 'attempted_at', 'delivered_at']
    list_filter = ['status', 'attempted_at', 'delivered_at']
    readonly_fields = ['attempted_at', 'delivered_at']


@admin.register(BroadcastNotification)
class BroadcastNotificationAdmin(admin.ModelAdmin):
    list_display = ['workspace', 'title', 'status', 'sent_count', 'total_recipients', 'created_at']
    list_filter = ['status', 'created_at', 'workspace']
    search_fields = ['title', 'message', 'workspace__name']
    readonly_fields = ['sent_at', 'total_recipients', 'sent_count', 'failed_count', 'read_count', 'created_at', 'updated_at']
