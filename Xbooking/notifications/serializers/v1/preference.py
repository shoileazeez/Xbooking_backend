"""
Notification Preference Serializers V1
"""
from rest_framework import serializers
from notifications.models import NotificationPreference


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user_email',
            'email_enabled', 'email_qr_code', 'email_order_confirmation', 
            'email_payment_confirmation', 'email_booking_reminder', 'email_booking_update',
            'sms_enabled', 'sms_qr_code', 'sms_booking_reminder',
            'push_enabled', 'push_qr_code', 'push_booking_reminder', 'push_booking_update',
            'in_app_enabled', 'in_app_qr_code', 'in_app_booking_reminder', 'in_app_booking_update',
            'digest_frequency', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_email', 'created_at', 'updated_at']


class UpdatePreferenceSerializer(serializers.ModelSerializer):
    """Serializer for updating notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'email_qr_code', 'email_order_confirmation', 
            'email_payment_confirmation', 'email_booking_reminder', 'email_booking_update',
            'sms_enabled', 'sms_qr_code', 'sms_booking_reminder',
            'push_enabled', 'push_qr_code', 'push_booking_reminder', 'push_booking_update',
            'in_app_enabled', 'in_app_qr_code', 'in_app_booking_reminder', 'in_app_booking_update',
            'digest_frequency'
        ]
