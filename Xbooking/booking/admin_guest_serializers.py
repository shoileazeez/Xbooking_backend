"""
Serializers for Admin Guest Management
"""
from rest_framework import serializers
from booking.models import Guest


class AdminVerifyGuestSerializer(serializers.Serializer):
    """Serializer for verifying a guest"""
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['notes']


class AdminRejectGuestSerializer(serializers.Serializer):
    """Serializer for rejecting a guest"""
    reason = serializers.CharField(
        max_length=500,
        required=True,
        help_text='Reason for rejecting the guest'
    )
    
    class Meta:
        fields = ['reason']


class AdminGuestListSerializer(serializers.ModelSerializer):
    """Serializer for listing guests in admin panel"""
    booking_id = serializers.CharField(source='booking.id', read_only=True)
    booking_space = serializers.CharField(source='booking.space.name', read_only=True)
    booker_email = serializers.CharField(source='booking.user.email', read_only=True)
    verified_by_email = serializers.CharField(source='verified_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Guest
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'booking_id', 'booking_space', 'booker_email',
            'verification_status', 'status',
            'verified_by_email', 'verified_at',
            'rejection_reason', 'created_at'
        ]
        read_only_fields = fields


class AdminGuestVerificationResponseSerializer(serializers.Serializer):
    """Response serializer for guest verification"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    guest = serializers.DictField()
    
    class Meta:
        fields = ['success', 'message', 'guest']
