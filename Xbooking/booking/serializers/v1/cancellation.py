"""
Booking Cancellation Serializers
"""
from rest_framework import serializers
from booking.models_cancellation import BookingCancellation
from booking.models import Booking


class BookingCancellationSerializer(serializers.ModelSerializer):
    """Serializer for booking cancellation"""
    
    booking_details = serializers.SerializerMethodField()
    cancelled_by_name = serializers.CharField(source='cancelled_by.full_name', read_only=True, allow_null=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    
    class Meta:
        model = BookingCancellation
        fields = [
            'id', 'booking', 'booking_details', 'cancelled_by', 'cancelled_by_name',
            'approved_by', 'approved_by_name', 'reason', 'reason_display',
            'reason_description', 'workspace_issues', 'found_alternative',
            'alternative_reason', 'would_book_again', 'suggestions',
            'rating_before_cancellation', 'contacted_workspace',
            'workspace_response_satisfactory', 'status', 'status_display',
            'original_amount', 'refund_percentage', 'refund_amount', 'penalty_amount',
            'refund_status', 'refund_reference', 'hours_until_checkin',
            'cancelled_at', 'approved_at', 'refunded_at', 'admin_notes',
            'cancellation_email_sent', 'refund_email_sent',
            'created_at', 'updated_at', 'is_refundable', 'is_approved', 'is_refunded'
        ]
        read_only_fields = [
            'id', 'status', 'original_amount', 'refund_percentage',
            'refund_amount', 'penalty_amount', 'refund_status',
            'refund_reference', 'hours_until_checkin', 'cancelled_at',
            'approved_at', 'approved_by', 'refunded_at', 'cancellation_email_sent',
            'refund_email_sent', 'created_at', 'updated_at'
        ]
    
    def get_booking_details(self, obj):
        """Get booking details"""
        booking = obj.booking
        return {
            'id': str(booking.id),
            'space_name': booking.space.name,
            'workspace_name': booking.workspace.name,
            'check_in': booking.check_in.isoformat(),
            'check_out': booking.check_out.isoformat(),
            'total_price': str(booking.total_price),
            'status': booking.status
        }


class RequestCancellationSerializer(serializers.Serializer):
    """Serializer for requesting booking cancellation with detailed feedback"""
    
    reason = serializers.ChoiceField(
        choices=BookingCancellation.CANCELLATION_REASON_CHOICES,
        required=True,
        help_text='Primary reason for cancellation'
    )
    reason_description = serializers.CharField(
        required=True,
        min_length=20,
        max_length=1000,
        help_text='Detailed explanation (minimum 20 characters)',
        error_messages={
            'min_length': 'Please provide at least 20 characters explaining your reason',
            'required': 'Please explain why you are cancelling this booking'
        }
    )
    
    # Additional feedback for workspace improvement
    workspace_issues = serializers.MultipleChoiceField(
        choices=[
            ('pricing', 'Pricing concerns'),
            ('location', 'Location issues'),
            ('amenities', 'Missing or inadequate amenities'),
            ('cleanliness', 'Cleanliness concerns'),
            ('accessibility', 'Accessibility problems'),
            ('communication', 'Poor communication from workspace'),
            ('availability', 'Unexpected unavailability'),
            ('policies', 'Restrictive policies'),
            ('other', 'Other issues')
        ],
        required=False,
        allow_empty=True,
        help_text='What issues did you experience? (Select all that apply)'
    )
    
    found_alternative = serializers.BooleanField(
        required=False,
        default=False,
        help_text='Did you find an alternative workspace?'
    )
    
    alternative_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text='If you found an alternative, what made it better?'
    )
    
    would_book_again = serializers.ChoiceField(
        choices=[
            ('yes', 'Yes, I would book this workspace again'),
            ('maybe', 'Maybe, depends on improvements'),
            ('no', 'No, I would not book again')
        ],
        required=False,
        help_text='Would you consider booking this workspace in the future?'
    )
    
    suggestions = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text='What could the workspace do to improve? (Optional but helpful)'
    )
    
    rating_before_cancellation = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5,
        help_text='How would you rate your experience so far? (1-5 stars)'
    )
    
    contacted_workspace = serializers.BooleanField(
        required=False,
        default=False,
        help_text='Did you try to contact the workspace before cancelling?'
    )
    
    workspace_response_satisfactory = serializers.BooleanField(
        required=False,
        help_text='If you contacted them, was their response satisfactory?'
    )
    
    def validate(self, data):
        """Validate the cancellation request"""
        # If found alternative, require reason
        if data.get('found_alternative') and not data.get('alternative_reason'):
            raise serializers.ValidationError({
                'alternative_reason': 'Please tell us what made the alternative better'
            })
        
        # If contacted workspace, require satisfaction response
        if data.get('contacted_workspace') and 'workspace_response_satisfactory' not in data:
            raise serializers.ValidationError({
                'workspace_response_satisfactory': 'Please let us know if their response was satisfactory'
            })
        
        return data


class ApproveCancellationSerializer(serializers.Serializer):
    """Serializer for approving cancellation"""
    
    custom_refund_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text='Optional custom refund amount (overrides policy)'
    )
    admin_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )


class RejectCancellationSerializer(serializers.Serializer):
    """Serializer for rejecting cancellation"""
    
    admin_notes = serializers.CharField(
        required=True,
        min_length=10,
        max_length=1000,
        help_text='Please provide reason for rejection'
    )
