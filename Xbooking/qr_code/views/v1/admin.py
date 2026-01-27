"""
Admin QR Code Views V1 - Admin QR code verification and check-in management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils import timezone

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from qr_code.models import BookingQRCode, CheckIn
from qr_code.serializers.v1 import (
    AdminVerifyQRCodeSerializer,
    CheckInSerializer,
    BookingQRCodeSerializer
)
from booking.models import Booking
from workspace.permissions import check_workspace_member


@extend_schema_view(
    list=extend_schema(description="List all QR codes in workspace (admin only)"),
    retrieve=extend_schema(description="Retrieve QR code details (admin only)"),
)
class AdminQRCodeViewSet(CachedModelViewSet):
    """Admin ViewSet for QR code verification and check-in management"""
    serializer_class = BookingQRCodeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 120  # 2 minutes cache for admin views
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        """Get QR codes for workspaces where user is admin/staff"""
        # Will be filtered by workspace_id in actions
        return BookingQRCode.objects.select_related(
            'booking', 'booking__space', 'booking__workspace', 'booking__user'
        ).order_by('-created_at')
    
    @extend_schema(
        request=AdminVerifyQRCodeSerializer,
        responses={200: CheckInSerializer}
    )
    @action(detail=False, methods=['post'], url_path='workspaces/(?P<workspace_id>[^/.]+)/check-in')
    def check_in(self, request, workspace_id=None):
        """Admin check-in a guest using QR code"""
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return ErrorResponse(
                message="You don't have permission to verify QR codes",
                status_code=403
            )
        
        serializer = AdminVerifyQRCodeSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid check-in data',
                errors=serializer.errors,
                status_code=400
            )
        
        verification_code = serializer.validated_data['verification_code']
        booking_id = serializer.validated_data['booking_id']
        notes = serializer.validated_data.get('notes', '')
        
        try:
            # Get QR code
            qr_code = BookingQRCode.objects.select_related('booking').get(
                verification_code=verification_code,
                booking_id=booking_id,
                booking__workspace_id=workspace_id
            )
            
            booking = qr_code.booking
            
            # Check if booking is confirmed
            if booking.status != 'confirmed':
                return ErrorResponse(
                    message=f'Booking must be confirmed for check-in. Current status: {booking.status}',
                    status_code=400
                )
            
            # Check if already checked in
            if booking.status == 'active':
                return ErrorResponse(
                    message='Booking is already checked in',
                    status_code=400
                )
            
            # Check if QR code is expired
            if qr_code.expires_at and qr_code.expires_at < timezone.now():
                return ErrorResponse(
                    message='QR code has expired',
                    status_code=400
                )
            
            # Mark QR code as verified
            qr_code.verified = True
            qr_code.verified_at = timezone.now()
            qr_code.scan_count += 1
            qr_code.save(update_fields=['verified', 'verified_at', 'scan_count'])
            
            # Create check-in record
            check_in = CheckIn.objects.create(
                booking=booking,
                checked_in_by=request.user,
                notes=notes
            )
            
            # Update booking status using service
            from booking.services import BookingService
            BookingService.check_in_booking(booking, request.user)
            
            serializer = CheckInSerializer(check_in)
            return SuccessResponse(
                message='Guest checked in successfully',
                data=serializer.data
            )
            
        except BookingQRCode.DoesNotExist:
            return ErrorResponse(
                message='Invalid QR code or booking',
                status_code=404
            )
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
    
    @extend_schema(
        responses={200: CheckInSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='workspaces/(?P<workspace_id>[^/.]+)/check-ins')
    def list_check_ins(self, request, workspace_id=None):
        """List all check-ins for a workspace"""
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return ErrorResponse(
                message="You don't have permission to view check-ins",
                status_code=403
            )
        
        check_ins = CheckIn.objects.filter(
            booking__workspace_id=workspace_id
        ).select_related(
            'booking', 'booking__space', 'booking__user', 'checked_in_by'
        ).order_by('-check_in_time')
        
        page = self.paginate_queryset(check_ins)
        if page is not None:
            serializer = CheckInSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CheckInSerializer(check_ins, many=True)
        return SuccessResponse(
            message='Check-ins retrieved successfully',
            data=serializer.data
        )
    
    @extend_schema(
        responses={200: BookingQRCodeSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='workspaces/(?P<workspace_id>[^/.]+)/qr-codes')
    def list_qr_codes(self, request, workspace_id=None):
        """List all QR codes for a workspace"""
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return ErrorResponse(
                message="You don't have permission to view QR codes",
                status_code=403
            )
        
        qr_codes = self.get_queryset().filter(
            booking__workspace_id=workspace_id
        )
        
        page = self.paginate_queryset(qr_codes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(qr_codes, many=True)
        return SuccessResponse(
            message='QR codes retrieved successfully',
            data=serializer.data
        )
