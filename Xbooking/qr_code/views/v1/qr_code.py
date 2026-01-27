"""
QR Code Views V1 - User QR code generation and retrieval
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.shortcuts import get_object_or_404

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from qr_code.models import OrderQRCode, BookingQRCode
from qr_code.serializers.v1 import (
    OrderQRCodeSerializer,
    BookingQRCodeSerializer,
    VerifyQRCodeSerializer
)
from qr_code.tasks import generate_order_receipt
from payment.models import Order
from booking.models import Booking


@extend_schema_view(
    list=extend_schema(description="List user's order QR codes"),
    retrieve=extend_schema(description="Retrieve order QR code details"),
)
class OrderQRCodeViewSet(CachedModelViewSet):
    """ViewSet for managing order QR codes"""
    serializer_class = OrderQRCodeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        return OrderQRCode.objects.filter(
            order__user=self.request.user
        ).select_related('order', 'order__user').order_by('-created_at')
    
    @extend_schema(
        request=None,
        responses={200: OrderQRCodeSerializer}
    )
    @action(detail=False, methods=['post'], throttle_classes=[ScopedRateThrottle])
    def generate(self, request):
        """Generate QR code for an order"""
        order_id = request.data.get('order_id')
        
        if not order_id:
            return ErrorResponse(
                message='Order ID is required',
                status_code=400
            )
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            
            # Check if order is paid
            if order.status not in ['paid', 'processing', 'completed']:
                return ErrorResponse(
                    message='QR code can only be generated for paid orders',
                    status_code=400
                )
            
            # Trigger QR code generation in background
            generate_order_receipt.delay(str(order.id))
            
            return SuccessResponse(
                message='QR code generation started. You will receive it via email shortly.',
                data={'order_id': str(order.id)}
            )
        except Order.DoesNotExist:
            return ErrorResponse(
                message='Order not found',
                status_code=404
            )
    
    @extend_schema(
        responses={200: OrderQRCodeSerializer}
    )
    @action(detail=False, methods=['get'], url_path='by-order/(?P<order_id>[^/.]+)')
    def by_order(self, request, order_id=None):
        """Get QR code for a specific order"""
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            qr_code = get_object_or_404(OrderQRCode, order=order)
            serializer = self.get_serializer(qr_code)
            
            return SuccessResponse(
                message='QR code retrieved successfully',
                data=serializer.data
            )
        except Order.DoesNotExist:
            return ErrorResponse(
                message='Order not found',
                status_code=404
            )


@extend_schema_view(
    list=extend_schema(description="List user's booking QR codes"),
    retrieve=extend_schema(description="Retrieve booking QR code details"),
)
class BookingQRCodeViewSet(CachedModelViewSet):
    """ViewSet for managing booking QR codes"""
    serializer_class = BookingQRCodeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 300
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        return BookingQRCode.objects.filter(
            booking__user=self.request.user
        ).select_related('booking', 'booking__space', 'booking__user').order_by('-created_at')
    
    @extend_schema(
        request=VerifyQRCodeSerializer,
        responses={200: BookingQRCodeSerializer}
    )
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """Verify a QR code"""
        serializer = VerifyQRCodeSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid verification data',
                errors=serializer.errors,
                status_code=400
            )
        
        verification_code = serializer.validated_data['verification_code']
        
        try:
            qr_code = BookingQRCode.objects.get(
                verification_code=verification_code,
                booking__user=request.user
            )
            
            # Increment scan count
            qr_code.scan_count += 1
            qr_code.save(update_fields=['scan_count'])
            
            serializer = self.get_serializer(qr_code)
            return SuccessResponse(
                message='QR code verified successfully',
                data=serializer.data
            )
        except BookingQRCode.DoesNotExist:
            return ErrorResponse(
                message='Invalid verification code',
                status_code=404
            )
    
    @extend_schema(
        responses={200: BookingQRCodeSerializer}
    )
    @action(detail=False, methods=['get'], url_path='by-booking/(?P<booking_id>[^/.]+)')
    def by_booking(self, request, booking_id=None):
        """Get QR code for a specific booking"""
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
            qr_code = get_object_or_404(BookingQRCode, booking=booking)
            serializer = self.get_serializer(qr_code)
            
            return SuccessResponse(
                message='QR code retrieved successfully',
                data=serializer.data
            )
        except Booking.DoesNotExist:
            return ErrorResponse(
                message='Booking not found',
                status_code=404
            )
