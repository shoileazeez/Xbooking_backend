"""
Broadcast Notification Serializers V1
"""
from rest_framework import serializers
from notifications.models import BroadcastNotification


class BroadcastNotificationSerializer(serializers.ModelSerializer):
    """Serializer for broadcast notifications"""
    
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = BroadcastNotification
        fields = [
            'id', 'workspace', 'workspace_name', 'created_by', 'created_by_email', 
            'title', 'message', 'channels', 'target_roles', 'status', 
            'scheduled_at', 'sent_at', 'total_recipients', 'sent_count', 
            'failed_count', 'read_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_by', 'created_by_email', 'workspace_name',
            'sent_at', 'total_recipients', 'sent_count', 'failed_count', 
            'read_count', 'created_at', 'updated_at'
        ]


class CreateBroadcastNotificationSerializer(serializers.ModelSerializer):
    """Serializer for creating broadcast notifications"""
    
    class Meta:
        model = BroadcastNotification
        fields = ['workspace', 'title', 'message', 'channels', 'target_users', 'target_roles', 'scheduled_at']
