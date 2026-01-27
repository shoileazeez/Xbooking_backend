"""
Payment V1 Views - Refund Management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404
from core.pagination import StandardResultsSetPagination
from core.responses import SuccessResponse, ErrorResponse
from core.views import CachedModelViewSet
from payment.models import Refund, Payment
from payment.serializers.v1 import (
    RefundSerializer,
    RefundListSerializer,
    CreateRefundSerializer,
)
from payment.services import PaymentService
import logging

logger = logging.getLogger(__name__)


class RefundViewSet(CachedModelViewSet):
    """ViewSet for refund management"""
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['status', 'reason', 'workspace']
    search_fields = ['order__order_number', 'payment__gateway_transaction_id']
    ordering_fields = ['requested_at', 'amount', 'status']
    ordering = ['-requested_at']
    
    def get_queryset(self):
        """Get refunds for current user"""
        user = self.request.user
        return Refund.objects.filter(
            Q(user=user) | Q(workspace__owner=user) | Q(workspace__members=user)
        ).select_related(
            'payment', 'order', 'workspace', 'user'
        ).distinct()
    
    def get_serializer_class(self):
        """Use optimized serializer for list view"""
        if self.action == 'list':
            return RefundListSerializer
        elif self.action == 'create':
            return CreateRefundSerializer
        return RefundSerializer
    
    def list(self, request, *args, **kwargs):
        """List user's refunds"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = RefundListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = RefundListSerializer(queryset, many=True)
        return SuccessResponse(data=serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Get refund details"""
        refund = self.get_object()
        serializer = self.get_serializer(refund)
        return SuccessResponse(data=serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Request a refund"""
        serializer = CreateRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment_id = serializer.validated_data['payment_id']
        reason = serializer.validated_data['reason']
        reason_description = serializer.validated_data['reason_description']
        amount = serializer.validated_data.get('amount')
        
        try:
            # Get payment
            payment = get_object_or_404(
                Payment.objects.filter(user=request.user),
                id=payment_id
            )
            
            # Check if payment is successful
            if payment.status != 'success':
                return Response(
                    ErrorResponse(message="Payment is not successful"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if refund already exists
            if payment.refunds.filter(status__in=['pending', 'processing', 'completed']).exists():
                return Response(
                    ErrorResponse(message="Refund already exists for this payment"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Request refund
            refund = PaymentService.request_refund(
                payment=payment,
                reason=reason,
                reason_description=reason_description,
                refund_amount=amount
            )
            
            response_serializer = RefundSerializer(refund)
            return Response(
                SuccessResponse(
                    data=response_serializer.data,
                    message="Refund requested successfully"
                ),
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error requesting refund: {str(e)}", exc_info=True)
            return Response(
                ErrorResponse(message="Failed to request refund"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


__all__ = ['RefundViewSet']
