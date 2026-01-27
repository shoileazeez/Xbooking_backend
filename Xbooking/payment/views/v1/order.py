"""
Payment V1 Views - Order Management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from core.pagination import StandardResultsSetPagination
from core.responses import SuccessResponse, ErrorResponse
from core.views import CachedModelViewSet
from payment.models import Order
from payment.serializers.v1 import (
    OrderSerializer,
    OrderListSerializer,
    CreateOrderSerializer,
)
from payment.services import PaymentService
from booking.models import Booking
import logging

logger = logging.getLogger(__name__)


class OrderViewSet(CachedModelViewSet):
    """ViewSet for order management"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['status', 'workspace']
    search_fields = ['order_number']
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get orders for current user"""
        user = self.request.user
        return Order.objects.filter(
            user=user
        ).select_related(
            'workspace', 'user'
        ).prefetch_related(
            Prefetch('bookings', queryset=Booking.objects.select_related('space'))
        ).distinct()
    
    def get_serializer_class(self):
        """Use optimized serializer for list view"""
        if self.action == 'list':
            return OrderListSerializer
        return OrderSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new order from bookings"""
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            order = PaymentService.create_order(
                booking_ids=serializer.validated_data['booking_ids'],
                user=request.user,
                notes=serializer.validated_data.get('notes')
            )
            
            response_serializer = OrderSerializer(order)
            return SuccessResponse(
                data=response_serializer.data,
                message="Order created successfully",
                status_code=201
            )
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}", exc_info=True)
            return Response(
                ErrorResponse(message="Failed to create order"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, *args, **kwargs):
        """Get order details"""
        order = self.get_object()
        serializer = self.get_serializer(order)
        return SuccessResponse(data=serializer.data)
    
    def list(self, request, *args, **kwargs):
        """List user's orders"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data)


__all__ = ['OrderViewSet']
