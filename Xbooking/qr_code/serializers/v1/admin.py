"""
Admin QR Code Serializers V1
"""
from rest_framework import serializers
from qr_code.models import CheckIn


class AdminVerifyQRCodeSerializer(serializers.Serializer):
    """Serializer for admin verifying QR code"""
    verification_code = serializers.CharField(required=True)
    booking_id = serializers.UUIDField(required=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['verification_code', 'booking_id', 'notes']


class AdminRejectQRCodeSerializer(serializers.Serializer):
    """Serializer for admin rejecting QR code"""
    verification_code = serializers.CharField(required=True)
    booking_id = serializers.UUIDField(required=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['verification_code', 'booking_id', 'reason']


class AdminResendQRCodeSerializer(serializers.Serializer):
    """Serializer for admin resending QR code"""
    email = serializers.EmailField(required=False)
    
    class Meta:
        fields = ['email']


class CheckInSerializer(serializers.ModelSerializer):
    """Serializer for check-in records"""
    booking_details = serializers.SerializerMethodField()
    checked_in_by_name = serializers.CharField(source='checked_in_by.get_full_name', read_only=True)
    
    class Meta:
        model = CheckIn
        fields = [
            'id', 'booking', 'booking_details', 'checked_in_by', 
            'checked_in_by_name', 'check_in_time', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'check_in_time', 'created_at']
    
    def get_booking_details(self, obj):
        """Get booking details"""
        return {
            'id': str(obj.booking.id),
            'space_name': obj.booking.space.name,
            'user_email': obj.booking.user.email,
            'status': obj.booking.status
        }
