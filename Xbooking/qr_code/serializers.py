"""
QR Code Serializers
"""
from rest_framework import serializers
from qr_code.models import OrderQRCode, QRCodeScanLog
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


class QRCodeScanLogSerializer(serializers.ModelSerializer):
    """Serializer for QR code scan logs"""
    scanned_by_email = serializers.CharField(source='scanned_by.email', read_only=True)
    
    class Meta:
        model = QRCodeScanLog
        fields = [
            'id', 'qr_code', 'scanned_by', 'scanned_by_email', 'scan_device_ip',
            'scan_result', 'scanned_at'
        ]
        read_only_fields = fields


class VerifyQRCodeSerializer(serializers.Serializer):
    """Serializer for verifying QR code"""
    verification_code = serializers.CharField(required=True, max_length=50)
    device_ip = serializers.CharField(required=False, allow_blank=True)
