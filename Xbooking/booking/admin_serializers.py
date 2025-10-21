"""
Serializers for Booking Admin Views
"""
from rest_framework import serializers


class AdminUpdateBookingStatusSerializer(serializers.Serializer):
    """Serializer for updating booking status"""
    status = serializers.ChoiceField(
        choices=['pending', 'confirmed', 'in_progress', 'completed', 'cancelled'],
        required=True
    )
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    class Meta:
        fields = ['status', 'notes']


class AdminBookingFilterSerializer(serializers.Serializer):
    """Serializer for booking filter parameters"""
    status = serializers.ChoiceField(
        choices=['pending', 'confirmed', 'in_progress', 'completed', 'cancelled'],
        required=False
    )
    space_id = serializers.CharField(required=False)
    user_email = serializers.EmailField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    
    class Meta:
        fields = ['status', 'space_id', 'user_email', 'date_from', 'date_to']
