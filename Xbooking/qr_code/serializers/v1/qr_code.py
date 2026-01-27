"""
QR Code Serializers V1
"""
from rest_framework import serializers
from qr_code.models import OrderQRCode, BookingQRCode, BookingQRCodeLog
from drf_spectacular.utils import extend_schema_field


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload endpoint"""
    file = serializers.FileField(required=True)
    file_type = serializers.CharField(
        required=False,
        help_text='Type of file: image, document, etc. (optional)'
    )
    
    def validate_file(self, file):
        """Validate uploaded file"""
        from django.conf import settings
        
        # Check file size
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes
        if file.size > max_size:
            raise serializers.ValidationError(
                f'File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB'
            )
        
        # Check file extension
        filename_parts = file.name.rsplit('.', 1)
        if len(filename_parts) < 2:
            raise serializers.ValidationError('File must have a valid extension')
        
        file_ext = filename_parts[1].lower()
        if file_ext not in settings.ALLOWED_FILE_TYPES:
            allowed = ', '.join(settings.ALLOWED_FILE_TYPES)
            raise serializers.ValidationError(
                f'File type .{file_ext} is not allowed. Allowed types: {allowed}'
            )
        
        return file


class FileUploadResponseSerializer(serializers.Serializer):
    """Serializer for file upload response"""
    success = serializers.BooleanField()
    file_id = serializers.CharField()
    file_url = serializers.URLField()
    filename = serializers.CharField()
    size = serializers.IntegerField()
    message = serializers.CharField(required=False)


class OrderQRCodeSerializer(serializers.ModelSerializer):
    """Serializer for order QR code"""
    qr_code_url = serializers.CharField(source='qr_code_image_url', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = OrderQRCode
        fields = [
            'id', 'order', 'order_number', 'verification_code', 'qr_code_url',
            'status', 'scan_count', 'verified', 'verified_at', 'expires_at',
            'created_at', 'sent_at'
        ]
        read_only_fields = [
            'id', 'order', 'order_number', 'verification_code', 'qr_code_url',
            'status', 'scan_count', 'verified', 'verified_at', 'created_at', 'sent_at'
        ]


class BookingQRCodeSerializer(serializers.ModelSerializer):
    """Serializer for booking QR code"""
    qr_code_url = serializers.CharField(source='qr_code_image_url', read_only=True)
    booking_details = serializers.SerializerMethodField()
    
    class Meta:
        model = BookingQRCode
        fields = [
            'id', 'booking', 'booking_details', 'verification_code', 'qr_code_url',
            'status', 'scan_count', 'verified', 'verified_at', 'expires_at',
            'created_at', 'sent_at'
        ]
        read_only_fields = [
            'id', 'booking', 'verification_code', 'qr_code_url',
            'status', 'scan_count', 'verified', 'verified_at', 'created_at', 'sent_at'
        ]
    
    @extend_schema_field(serializers.DictField())
    def get_booking_details(self, obj):
        """Get booking details"""
        if obj.booking:
            return {
                'id': str(obj.booking.id),
                'space_name': obj.booking.space.name,
                'check_in': obj.booking.check_in.isoformat(),
                'check_out': obj.booking.check_out.isoformat(),
                'status': obj.booking.status
            }
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
    verification_code = serializers.CharField(required=True)
    
    class Meta:
        fields = ['verification_code']
