"""
Guest Serializers for Booking Management
"""
from rest_framework import serializers
from booking.models import Guest


class GuestSerializer(serializers.ModelSerializer):
    """Serializer for guest information"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Guest
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'status', 'qr_code_sent', 'qr_code_sent_at', 'checked_in_at',
            'checked_out_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'qr_code_sent', 'qr_code_sent_at', 'checked_in_at',
            'checked_out_at', 'created_at', 'status'
        ]
    
    def get_full_name(self, obj):
        """Get guest full name"""
        return f"{obj.first_name} {obj.last_name}"


class CreateGuestSerializer(serializers.ModelSerializer):
    """Serializer for creating guests"""
    
    class Meta:
        model = Guest
        fields = ['first_name', 'last_name', 'email', 'phone']
    
    def validate_email(self, value):
        """Validate email format"""
        if not value:
            raise serializers.ValidationError("Email is required")
        return value.lower()


class AddGuestsSerializer(serializers.Serializer):
    """Serializer for adding multiple guests to a booking"""
    guests = CreateGuestSerializer(many=True, required=True)
    
    class Meta:
        fields = ['guests']
    
    def validate_guests(self, value):
        """Validate at least one guest"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one guest is required")
        return value


class GuestCheckInSerializer(serializers.Serializer):
    """Serializer for guest check-in"""
    verification_code = serializers.CharField(required=True)
    
    class Meta:
        fields = ['verification_code']


class GuestCheckOutSerializer(serializers.Serializer):
    """Serializer for guest check-out"""
    verification_code = serializers.CharField(required=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['verification_code', 'notes']


class GuestQRCodeSerializer(serializers.Serializer):
    """Response serializer for guest QR code"""
    guest_id = serializers.CharField()
    verification_code = serializers.CharField()
    guest_name = serializers.CharField()
    booking_id = serializers.CharField()
    space_name = serializers.CharField()
    check_in = serializers.DateTimeField()
    check_out = serializers.DateTimeField()
    
    class Meta:
        fields = [
            'guest_id', 'verification_code', 'guest_name',
            'booking_id', 'space_name', 'check_in', 'check_out'
        ]


class BookingGuestListSerializer(serializers.Serializer):
    """Serializer for listing guests in a booking"""
    booking_id = serializers.CharField()
    total_guests = serializers.IntegerField()
    checked_in_count = serializers.IntegerField()
    guests = GuestSerializer(many=True)
    
    class Meta:
        fields = ['booking_id', 'total_guests', 'checked_in_count', 'guests']
