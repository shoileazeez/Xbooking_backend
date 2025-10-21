"""
Notification serializers
"""
from rest_framework import serializers
from notifications.models import Notification, NotificationPreference, BroadcastNotification, NotificationLog


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 
            'email_enabled', 'email_qr_code', 'email_order_confirmation', 
            'email_payment_confirmation', 'email_booking_reminder', 'email_booking_update',
            'sms_enabled', 'sms_qr_code', 'sms_booking_reminder',
            'push_enabled', 'push_qr_code', 'push_booking_reminder', 'push_booking_update',
            'in_app_enabled', 'in_app_qr_code', 'in_app_booking_reminder', 'in_app_booking_update',
            'digest_frequency', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification delivery logs"""
    
    class Meta:
        model = NotificationLog
        fields = ['id', 'notification', 'status', 'attempt_number', 'error_message', 'response_code', 'attempted_at', 'delivered_at']
        read_only_fields = ['id', 'attempted_at', 'delivered_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    
    delivery_logs = NotificationLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'channel', 'title', 'message', 'data',
            'is_read', 'is_sent', 'is_clicked', 'sent_at', 'read_at', 'clicked_at',
            'created_at', 'updated_at', 'delivery_logs'
        ]
        read_only_fields = ['id', 'user', 'is_sent', 'sent_at', 'read_at', 'clicked_at', 'created_at', 'updated_at']


class NotificationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for notifications with full information"""
    
    delivery_logs = NotificationLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'channel', 'title', 'message', 'data',
            'is_read', 'is_sent', 'is_clicked', 'sent_at', 'read_at', 'clicked_at',
            'created_at', 'updated_at', 'delivery_logs'
        ]
        read_only_fields = ['id', 'user', 'is_sent', 'sent_at', 'read_at', 'clicked_at', 'created_at', 'updated_at']


class BroadcastNotificationSerializer(serializers.ModelSerializer):
    """Serializer for broadcast notifications"""
    
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = BroadcastNotification
        fields = [
            'id', 'workspace', 'workspace_name', 'created_by', 'created_by_email', 'title', 'message', 
            'channels', 'target_roles', 'status', 'scheduled_at', 'sent_at',
            'total_recipients', 'sent_count', 'failed_count', 'read_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'sent_at', 'total_recipients', 'sent_count', 'failed_count', 'read_count', 'created_at', 'updated_at']


class CreateBroadcastNotificationSerializer(serializers.ModelSerializer):
    """Serializer for creating broadcast notifications"""
    
    class Meta:
        model = BroadcastNotification
        fields = ['workspace', 'title', 'message', 'channels', 'target_users', 'target_roles', 'scheduled_at']
