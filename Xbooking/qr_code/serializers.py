"""
QR Code Serializers
"""
from rest_framework import serializers
from qr_code.models import OrderQRCode, BookingQRCode, CheckIn, BookingQRCodeLog
from drf_spectacular.utils import extend_schema_field


class OrderQRCodeSerializer(serializers.ModelSerializer):
    """Serializer for QR code"""
    qr_code_url = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderQRCode
        fields = [
            'id', 'order', 'verification_code', 'qr_code_url', 'qr_code_image',
            'status', 'scan_count', 'verified', 'verified_at', 'expires_at',
            'created_at', 'sent_at'
        ]
        read_only_fields = [
            'id', 'order', 'verification_code', 'qr_code_url', 'qr_code_image',
            'status', 'scan_count', 'verified', 'verified_at', 'created_at', 'sent_at'
        ]
    
    @extend_schema_field(serializers.CharField())
    def get_qr_code_url(self, obj):
        """Get full URL for QR code image"""
        if obj.qr_code_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code_image.url)
            return obj.qr_code_image.url
        return None


class BookingQRCodeLogSerializer(serializers.ModelSerializer):
    """Serializer for QR code logs"""
    qr_code_id = serializers.CharField(source='qr_code.id', read_only=True)
    
    class Meta:
        model = BookingQRCodeLog
        fields = [
            'id', 'qr_code_id', 'action', 'details', 'timestamp'
        ]
        read_only_fields = fields


class VerifyQRCodeSerializer(serializers.Serializer):
    """Serializer for verifying QR code"""
    verification_code = serializers.CharField(required=True, max_length=50)
    device_ip = serializers.CharField(required=False, allow_blank=True)


class BookingQRCodeSerializer(serializers.ModelSerializer):
    """Serializer for per-booking QR codes"""
    booking_id = serializers.CharField(source='booking.id', read_only=True)
    space_name = serializers.CharField(source='booking.space.name', read_only=True)
    guest_email = serializers.CharField(source='booking.user.email', read_only=True)
    qr_code_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BookingQRCode
        fields = [
            'id', 'booking_id', 'space_name', 'guest_email', 'qr_code_url',
            'qr_code_image', 'verification_code', 'status', 'used', 
            'total_check_ins', 'max_check_ins', 'expires_at',
            'created_at', 'sent_at'
        ]
        read_only_fields = [
            'id', 'qr_code_url', 'qr_code_image', 'status', 'used',
            'total_check_ins', 'created_at', 'sent_at'
        ]
    
    @extend_schema_field(serializers.CharField())
    def get_qr_code_url(self, obj):
        """Get full URL for QR code image"""
        if obj.qr_code_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code_image.url)
            return obj.qr_code_image.url
        return None


class CheckInSerializer(serializers.ModelSerializer):
    """Serializer for check-in/check-out records"""
    booking_id = serializers.CharField(source='booking.id', read_only=True)
    qr_code_id = serializers.CharField(source='qr_code.id', read_only=True)
    verified_by_email = serializers.CharField(source='verified_by.email', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = CheckIn
        fields = [
            'id', 'booking_id', 'qr_code_id', 'check_in_time', 'check_out_time',
            'duration_minutes', 'verified_by_email', 'notes', 'created_at'
        ]
        read_only_fields = fields
    
    @extend_schema_field(serializers.IntegerField())
    def get_duration_minutes(self, obj):
        """Calculate duration in minutes"""
        if obj.check_in_time and obj.check_out_time:
            delta = obj.check_out_time - obj.check_in_time
            return int(delta.total_seconds() / 60)
        return None
