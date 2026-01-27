"""
Booking Review Views V1
"""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from booking.models import BookingReview, Booking
from booking.serializers.v1 import BookingReviewSerializer, CreateReviewSerializer


@extend_schema_view(
    list=extend_schema(description="List user's booking reviews"),
    retrieve=extend_schema(description="Retrieve review details"),
    create=extend_schema(description="Create a booking review"),
)
class BookingReviewViewSet(CachedModelViewSet):
    """ViewSet for managing booking reviews"""
    serializer_class = BookingReviewSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 600
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        user = self.request.user
        return BookingReview.objects.filter(
            user=user
        ).select_related('booking', 'space', 'user').order_by('-created_at')
    
    def create(self, request):
        """Create a booking review"""
        serializer = CreateReviewSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid review data',
                errors=serializer.errors,
                status_code=400
            )
        
        booking_id = serializer.validated_data['booking_id']
        rating = serializer.validated_data['rating']
        comment = serializer.validated_data.get('comment', '')
        
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return ErrorResponse(
                message='Booking not found',
                status_code=404
            )
        
        # Create review
        review = BookingReview.objects.create(
            booking=booking,
            user=request.user,
            space=booking.space,
            rating=rating,
            comment=comment
        )
        
        serializer = BookingReviewSerializer(review)
        return SuccessResponse(
            message='Review created successfully',
            data=serializer.data,
            status_code=201
        )
