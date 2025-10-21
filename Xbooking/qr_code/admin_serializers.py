"""
Serializers for QR Code Admin Views
"""
from rest_framework import serializers


class AdminVerifyQRCodeSerializer(serializers.Serializer):
    """Serializer for verifying QR code"""
    qr_code_id = serializers.CharField(required=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['qr_code_id', 'notes']


class AdminRejectQRCodeSerializer(serializers.Serializer):
    """Serializer for rejecting QR code"""
    qr_code_id = serializers.CharField(required=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['qr_code_id', 'reason']


class AdminResendQRCodeSerializer(serializers.Serializer):
    """Serializer for resending QR code"""
    email = serializers.EmailField(required=False)
    
    class Meta:
        fields = ['email']
