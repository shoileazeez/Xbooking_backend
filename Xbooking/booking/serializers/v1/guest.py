"""
Guest Serializers V1
"""
from rest_framework import serializers
from booking.models import Guest


class GuestSerializer(serializers.ModelSerializer):
    """Serializer for guest details"""
    booking_number = serializers.CharField(source='booking.id', read_only=True)
    space_name = serializers.CharField(source='booking.space.name', read_only=True)
    
    class Meta:
        model = Guest
        fields = [
            'id', 'booking', 'booking_number', 'space_name',
            'first_name', 'last_name', 'email', 'phone',
            'status', 'qr_code_url', 'verification_code',
            'is_email_verified', 'is_phone_verified',
            'checked_in_at', 'checked_out_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'qr_code_url', 'verification_code',
            'is_email_verified', 'is_phone_verified',
            'checked_in_at', 'checked_out_at',
            'created_at', 'updated_at'
        ]


class AddGuestSerializer(serializers.Serializer):
    """Serializer for adding a guest to booking"""
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)


class AddGuestsSerializer(serializers.Serializer):
    """Serializer for adding multiple guests to booking"""
    guests = serializers.ListField(
        child=AddGuestSerializer(),
        min_length=1,
        help_text="List of guests to add"
    )


class GuestCheckInSerializer(serializers.Serializer):
    """Serializer for guest check-in"""
    verification_code = serializers.CharField(
        required=False,
        help_text="Guest verification code (optional if using QR)"
    )


class GuestCheckOutSerializer(serializers.Serializer):
    """Serializer for guest check-out"""
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional checkout notes"
    )


__all__ = [
    'GuestSerializer',
    'AddGuestSerializer',
    'AddGuestsSerializer',
    'GuestCheckInSerializer',
    'GuestCheckOutSerializer',
]
