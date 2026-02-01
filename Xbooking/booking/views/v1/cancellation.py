"""
Booking Cancellation Views
"""
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from booking.models import Booking
from booking.models_cancellation import BookingCancellation
from booking.services import BookingService
from booking.serializers.v1.cancellation import (
    BookingCancellationSerializer,
    RequestCancellationSerializer,
    ApproveCancellationSerializer,
    RejectCancellationSerializer
)
from workspace.permissions import check_workspace_member


class BookingCancellationViewSet(CachedModelViewSet):
    """ViewSet for booking cancellations"""
    serializer_class = BookingCancellationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 120
    http_method_names = ['get', 'post']
    """Serializer for booking cancellation"""
    booking_details = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='cancelled_by.full_name', read_only=True)
    
    class Meta:
        model = BookingCancellation
        fields = [
            'id', 'booking', 'booking_details', 'cancelled_by', 'user_name',
            'reason', 'reason_description', 'status', 'original_amount',
            'refund_percentage', 'refund_amount', 'penalty_amount',
            'refund_status', 'refund_reference', 'hours_until_checkin',
            'cancelled_at', 'approved_at', 'approved_by', 'refunded_at',
            'admin_notes', 'cancellation_email_sent', 'refund_email_sent',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'original_amount', 'refund_percentage',
            'refund_amount', 'penalty_amount', 'refund_status',
            'refund_reference', 'hours_until_checkin', 'cancelled_at',
            'approved_at', 'approved_by', 'refunded_at', 'created_at', 'updated_at'
        ]
    
    
    def get_queryset(self):
        """Get cancellations for user"""
        return BookingCancellation.objects.filter(
            booking__user=self.request.user
        ).select_related(
            'booking', 'booking__space', 'booking__workspace',
            'cancelled_by', 'approved_by'
        ).order_by('-cancelled_at')
    
    @extend_schema(
        request=RequestCancellationSerializer,
        responses={201: BookingCancellationSerializer}
    )
    @action(detail=False, methods=['post'], url_path='booking/(?P<booking_id>[^/.]+)/cancel')
    def request_cancellation(self, request, booking_id=None):
        """Request booking cancellation"""
        serializer = RequestCancellationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid cancellation request',
                errors=serializer.errors,
                status_code=400
            )
        
        try:
            # Get booking
            booking = get_object_or_404(
                Booking,
                id=booking_id,
                user=request.user
            )
            
            # Cancel booking using service (creates cancellation record automatically)
            booking, cancellation = BookingService.cancel_booking(
                booking=booking,
                cancelled_by=request.user,
                reason=serializer.validated_data['reason'],
                reason_description=serializer.validated_data['reason_description']
            )
            
            # Update cancellation with additional feedback
            cancellation.workspace_issues = list(serializer.validated_data.get('workspace_issues', []))
            cancellation.found_alternative = serializer.validated_data.get('found_alternative', False)
            cancellation.alternative_reason = serializer.validated_data.get('alternative_reason', '')
            cancellation.would_book_again = serializer.validated_data.get('would_book_again', None)
            cancellation.suggestions = serializer.validated_data.get('suggestions', '')
            cancellation.rating_before_cancellation = serializer.validated_data.get('rating_before_cancellation', None)
            cancellation.contacted_workspace = serializer.validated_data.get('contacted_workspace', False)
            cancellation.workspace_response_satisfactory = serializer.validated_data.get('workspace_response_satisfactory', None)
            cancellation.save()
            
            # Serialize and return
            serializer = BookingCancellationSerializer(cancellation)
            return SuccessResponse(
                message='Booking cancellation processed successfully',
                data=serializer.data,
                status_code=201
            )
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
        except Exception as e:
            return ErrorResponse(
                message=f'Cancellation failed: {str(e)}',
                status_code=500
            )
    
    @extend_schema(
        responses={200: BookingCancellationSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def my_cancellations(self, request):
        """Get user's cancellation history"""
        cancellations = self.get_queryset()
        
        page = self.paginate_queryset(cancellations)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(cancellations, many=True)
        return SuccessResponse(
            message='Cancellations retrieved successfully',
            data=serializer.data
        )
    
    @extend_schema(
        responses={200: BookingCancellationSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='workspace/(?P<workspace_id>[^/.]+)/pending')
    def workspace_pending(self, request, workspace_id=None):
        """Get pending cancellations for workspace (admin only)"""
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return ErrorResponse(
                message="You don't have permission to view cancellations",
                status_code=403
            )
        
        cancellations = BookingCancellation.objects.filter(
            booking__workspace_id=workspace_id,
            status='pending'
        ).select_related(
            'booking', 'booking__space', 'booking__user',
            'cancelled_by'
        ).order_by('-cancelled_at')
        
        page = self.paginate_queryset(cancellations)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(cancellations, many=True)
        return SuccessResponse(
            message='Pending cancellations retrieved successfully',
            data=serializer.data
        )
    
    @extend_schema(
        request=ApproveCancellationSerializer,
        responses={200: BookingCancellationSerializer}
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve cancellation (admin only)"""
        cancellation = get_object_or_404(BookingCancellation, id=pk)
        
        # Check permission
        if not check_workspace_member(
            request.user,
            cancellation.booking.workspace.id,
            ['admin']
        ):
            return ErrorResponse(
                message="Only workspace admins can approve cancellations",
                status_code=403
            )
        
        if cancellation.status != 'pending':
            return ErrorResponse(
                message=f'Cannot approve cancellation with status: {cancellation.status}',
                status_code=400
            )
        
        serializer = ApproveCancellationSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid request',
                errors=serializer.errors,
                status_code=400
            )
        
        try:
            # Approve using service
            booking, cancellation = BookingService.approve_cancellation(
                cancellation=cancellation,
                approved_by=request.user,
                custom_refund_amount=serializer.validated_data.get('custom_refund_amount'),
                admin_notes=serializer.validated_data.get('admin_notes', '')
            )
            
            serializer = BookingCancellationSerializer(cancellation)
            return SuccessResponse(
                message='Cancellation approved and refund processed',
                data=serializer.data
            )
        except Exception as e:
            return ErrorResponse(
                message=f'Failed to approve cancellation: {str(e)}',
                status_code=500
            )
    
    @extend_schema(
        request=RejectCancellationSerializer,
        responses={200: BookingCancellationSerializer}
    )
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject cancellation (admin only)"""
        cancellation = get_object_or_404(BookingCancellation, id=pk)
        
        # Check permission
        if not check_workspace_member(
            request.user,
            cancellation.booking.workspace.id,
            ['admin']
        ):
            return ErrorResponse(
                message="Only workspace admins can reject cancellations",
                status_code=403
            )
        
        if cancellation.status != 'pending':
            return ErrorResponse(
                message=f'Cannot reject cancellation with status: {cancellation.status}',
                status_code=400
            )
        
        serializer = RejectCancellationSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid request',
                errors=serializer.errors,
                status_code=400
            )
        
        try:
            # Reject using service
            cancellation = BookingService.reject_cancellation(
                cancellation=cancellation,
                rejected_by=request.user,
                rejection_reason=serializer.validated_data['admin_notes']
            )
            
            serializer = BookingCancellationSerializer(cancellation)
            return SuccessResponse(
                message='Cancellation rejected',
                data=serializer.data
            )
        except Exception as e:
            return ErrorResponse(
                message=f'Failed to reject cancellation: {str(e)}',
                status_code=500
            )
