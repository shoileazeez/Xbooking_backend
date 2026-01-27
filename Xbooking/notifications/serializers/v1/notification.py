"""
Notification Serializers V1
"""
from rest_framework import serializers
from notifications.models import Notification, NotificationLog


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification delivery logs"""
    
    class Meta:
        model = NotificationLog
        fields = ['id', 'notification', 'status', 'attempt_number', 'error_message', 'response_code', 'attempted_at', 'delivered_at']
        read_only_fields = ['id', 'attempted_at', 'delivered_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications list"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'channel', 'title', 'message', 
            'is_read', 'is_sent', 'is_clicked', 
            'sent_at', 'read_at', 'clicked_at', 'created_at'
        ]
        read_only_fields = fields


class NotificationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for notifications with full information"""
    
    delivery_logs = NotificationLogSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user_email', 'notification_type', 'channel', 'title', 'message', 'data',
            'is_read', 'is_sent', 'is_clicked', 
            'sent_at', 'read_at', 'clicked_at', 'created_at', 'updated_at', 
            'delivery_logs'
        ]
        read_only_fields = fields


class MarkNotificationReadSerializer(serializers.Serializer):
    """Serializer for marking notification as read"""
    
    is_read = serializers.BooleanField(default=True)
    is_clicked = serializers.BooleanField(required=False, default=False)


class BulkMarkReadSerializer(serializers.Serializer):
    """Serializer for bulk marking notifications as read"""
    
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of notification IDs to mark as read. If omitted, marks all as read."
    )
    mark_all = serializers.BooleanField(default=False, help_text="Mark all unread notifications as read")
