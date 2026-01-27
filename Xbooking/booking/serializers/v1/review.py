"""
Booking Review Serializers V1
"""
from rest_framework import serializers

from booking.models import BookingReview
from user.serializers.v1 import UserMinimalSerializer


class BookingReviewSerializer(serializers.ModelSerializer):
    """Serializer for booking reviews"""
    user_details = UserMinimalSerializer(source='user', read_only=True)
    space_name = serializers.CharField(source='space.name', read_only=True)
    
    class Meta:
        model = BookingReview
        fields = [
            'id', 'booking', 'user', 'user_details', 'space',
            'space_name', 'rating', 'comment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_rating(self, value):
        """Validate rating is between 1-5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating must be between 1 and 5')
        return value


class CreateReviewSerializer(serializers.Serializer):
    """Serializer for creating a booking review"""
    booking_id = serializers.UUIDField(required=True)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
    
    def validate_booking_id(self, value):
        """Validate booking exists and belongs to user"""
        from booking.models import Booking
        
        try:
            booking = Booking.objects.get(id=value)
        except Booking.DoesNotExist:
            raise serializers.ValidationError('Booking not found')
        
        # Check booking is completed
        if booking.status != 'completed':
            raise serializers.ValidationError('Can only review completed bookings')
        
        # Check no existing review
        if hasattr(booking, 'review'):
            raise serializers.ValidationError('Booking already has a review')
        
        return value
