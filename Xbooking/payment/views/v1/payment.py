"""
Payment V1 Views - Payment Processing
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
from payment.models import Payment, Order
from payment.serializers.v1 import (
    PaymentSerializer,
    PaymentListSerializer,
    InitiatePaymentSerializer,
    PaymentCallbackSerializer,
    PaymentStatusSerializer,
)
from payment.services import PaymentService
from payment.gateways import PaystackGateway, FlutterwaveGateway
import logging

logger = logging.getLogger(__name__)


class PaymentViewSet(CachedModelViewSet):
    """ViewSet for payment management"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['status', 'payment_method', 'workspace']
    search_fields = ['gateway_transaction_id', 'order__order_number']
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get payments for current user"""
        user = self.request.user
        return Payment.objects.filter(
            Q(user=user) | Q(workspace__admin=user)
        ).select_related(
            'order', 'workspace', 'user'
        ).distinct()
    
    def get_serializer_class(self):
        """Use optimized serializer for list view"""
        if self.action == 'list':
            return PaymentListSerializer
        elif self.action == 'initiate':
            return InitiatePaymentSerializer
        elif self.action == 'callback':
            return PaymentCallbackSerializer
        elif self.action == 'check_status':
            return PaymentStatusSerializer
        return PaymentSerializer
    
    def list(self, request, *args, **kwargs):
        """List user's payments"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Get payment details"""
        payment = self.get_object()
        serializer = self.get_serializer(payment)
        return SuccessResponse(data=serializer.data)
    
    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """Initiate a payment for an order"""
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order_id = serializer.validated_data['order_id']
        payment_method = serializer.validated_data['payment_method']
        
        try:
            # Get order
            order = get_object_or_404(
                Order.objects.filter(user=request.user),
                id=order_id
            )
            
            # Check if order is pending
            if order.status != 'pending':
                return Response(
                    ErrorResponse(message="Order is not pending"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if payment already exists
            if hasattr(order, 'payment') and order.payment.status in ['success', 'processing']:
                return Response(
                    ErrorResponse(message="Payment already exists for this order"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Handle wallet payment separately
            if payment_method == 'wallet':
                # Process wallet payment directly
                payment = PaymentService.pay_with_wallet(
                    order=order,
                    user=request.user
                )
                
                return SuccessResponse(
                    data={
                        'payment_id': str(payment.id),
                        'status': payment.status,
                        'message': 'Payment completed using wallet'
                    },
                    message="Payment completed successfully using wallet"
                )
            
            # Get gateway handler for other payment methods
            if payment_method == 'paystack':
                gateway = PaystackGateway()
            elif payment_method == 'flutterwave':
                gateway = FlutterwaveGateway()
            else:
                return Response(
                    ErrorResponse(message="Unsupported payment method"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initiate payment
            payment, gateway_response = PaymentService.initiate_payment(
                order=order,
                payment_method=payment_method,
                gateway_handler=gateway
            )
            
            # Check if gateway initialization was successful
            if not gateway_response.get('success', False):
                error_msg = gateway_response.get('error', 'Payment gateway initialization failed')
                logger.error(f"Gateway initialization failed: {error_msg}")
                logger.error(f"Gateway response: {gateway_response}")
                return ErrorResponse(
                    message=f"Payment gateway error: {error_msg}",
                    status_code=400
                )
            
            return SuccessResponse(
                data={
                    'payment_id': str(payment.id),
                    'authorization_url': gateway_response.get('authorization_url'),
                    'access_code': gateway_response.get('access_code'),
                    'reference': gateway_response.get('reference'),
                },
                message="Payment initiated successfully"
            )
            
        except Exception as e:
            logger.error(f"Error initiating payment: {str(e)}", exc_info=True)
            return ErrorResponse(
                message=str(e),
                status_code=500
            )
    
    @action(detail=False, methods=['post'])
    def pay_with_wallet(self, request):
        """Pay for an order using wallet balance"""
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order_id = serializer.validated_data['order_id']
        
        try:
            # Get order
            order = get_object_or_404(
                Order.objects.filter(user=request.user),
                id=order_id
            )
            
            # Check if order is pending
            if order.status != 'pending':
                return Response(
                    ErrorResponse(message="Order is not pending"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if payment already exists
            if hasattr(order, 'payment') and order.payment.status in ['success', 'processing']:
                return Response(
                    ErrorResponse(message="Payment already exists for this order"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process wallet payment
            payment = PaymentService.pay_with_wallet(
                order=order,
                user=request.user
            )
            
            return SuccessResponse(
                data=PaymentSerializer(payment).data,
                message="Payment completed successfully using wallet"
            )
            
        except ValueError as e:
            return ErrorResponse(
                message=str(e),
                status_code=400
            )
        except Exception as e:
            logger.error(f"Error processing wallet payment: {str(e)}", exc_info=True)
            return ErrorResponse(
                message="Failed to process wallet payment",
                status_code=500
            )
    
    @action(detail=False, methods=['post', 'get'])
    def callback(self, request):
        """Handle payment callback from gateway"""
        serializer = PaymentCallbackSerializer(data=request.query_params if request.method == 'GET' else request.data)
        serializer.is_valid(raise_exception=True)
        
        reference = serializer.validated_data['reference']
        
        import logging
        logger = logging.getLogger(__name__)
        try:
            # Get payment by reference
            payment = get_object_or_404(
                Payment,
                gateway_transaction_id=reference
            )
            # Verify payment with gateway
            if payment.payment_method == 'paystack':
                gateway = PaystackGateway()
            elif payment.payment_method == 'flutterwave':
                gateway = FlutterwaveGateway()
            else:
                logger.error(f"Payment callback: Unsupported payment method {payment.payment_method}")
                return ErrorResponse(
                    message="Unsupported payment method",
                    status_code=400
                )
            verification = gateway.verify_transaction(reference)
            logger.error(f"Payment callback verification response: {verification}")
            status_val = verification.get('status')
            if status_val in ['success', 'successful']:
                # Complete payment
                PaymentService.complete_payment(payment, verification)
                logger.error(f"Payment callback: Payment completed successfully for {reference}")
                return SuccessResponse(
                    data=PaymentStatusSerializer(payment).data,
                    message="Payment verified successfully"
                )
            else:
                # Fail payment
                PaymentService.fail_payment(payment, verification.get('message', 'Payment verification failed'))
                logger.error(f"Payment callback: Payment verification failed for {reference} - {verification}")
                return ErrorResponse(
                    message="Payment verification failed",
                    errors=PaymentStatusSerializer(payment).data,
                    status_code=400
                )
        except Exception as e:
            logger.error(f"Error processing payment callback: {str(e)}", exc_info=True)
            return ErrorResponse(
                message="Failed to process payment callback",
                status_code=500
            )
    
    @action(detail=True, methods=['get'])
    def check_status(self, request, pk=None):
        """Check payment status"""
        payment = self.get_object()
        serializer = PaymentStatusSerializer(payment)
        return SuccessResponse(data=serializer.data)


__all__ = ['PaymentViewSet']
