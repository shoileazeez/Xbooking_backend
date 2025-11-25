"""
Serializers for Admin Guest Management
"""
from rest_framework import serializers
from booking.models import Guest


class AdminGuestListSerializer(serializers.ModelSerializer):
    """Serializer for listing guests in admin panel"""
    booking_id = serializers.CharField(source='booking.id', read_only=True)
    booking_space = serializers.CharField(source='booking.space.name', read_only=True)
    booker_email = serializers.CharField(source='booking.user.email', read_only=True)
    checked_in_by_email = serializers.CharField(source='checked_in_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Guest
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'booking_id', 'booking_space', 'booker_email',
            'status', 'checked_in_by_email', 'checked_in_at', 
            'checked_out_at', 'created_at'
        ]
        read_only_fields = fields
