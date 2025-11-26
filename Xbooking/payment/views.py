"""
Payment and Order API Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from payment.models import Order, Payment, Refund, PaymentWebhook
from payment.serializers import (
    OrderSerializer, CreateOrderSerializer, PaymentSerializer,
    InitiatePaymentSerializer, PaymentCallbackSerializer, RefundSerializer,
    CreateRefundSerializer, OrderListSerializer, PaymentListSerializer
)
from booking.models import Booking
from workspace.permissions import check_workspace_member
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
import requests
import logging

logger = logging.getLogger(__name__)

from qr_code.tasks import (
    generate_qr_code_for_order, send_qr_code_email,
    send_order_confirmation_email, send_payment_confirmation_email
)
from payment.gateways import PaystackGateway, FlutterwaveGateway


class CreateOrderView(APIView):
    """Create order from bookings"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Create order from bookings",
        description="Create an order from one or more bookings",
        tags=["Orders"],
        request=CreateOrderSerializer,
        responses={
            201: OrderSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request):
        """Create new order(s)"""
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            booking_ids = serializer.validated_data['booking_ids']
            bookings = Booking.objects.filter(
                id__in=booking_ids,
                user=request.user,
                status__in=['pending', 'confirmed']
            )
            
            if not bookings.exists():
                return Response(
                    {"detail": "No valid bookings found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if bookings.count() != len(booking_ids):
                return Response(
                    {"detail": "Some bookings not found or invalid"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Group bookings by workspace
            bookings_by_workspace = {}
            for booking in bookings:
                if booking.workspace_id not in bookings_by_workspace:
                    bookings_by_workspace[booking.workspace_id] = []
                bookings_by_workspace[booking.workspace_id].append(booking)
            
            created_orders = []
            
            for workspace_id, workspace_bookings in bookings_by_workspace.items():
                # Calculate totals for this workspace's order
                subtotal = sum(b.base_price for b in workspace_bookings)
                discount_amount = Decimal('0') # We might need to distribute discount if it was global, but for now assume 0 or per-booking
                # If discount was passed in request, it's tricky. Let's assume discount is 0 for now or handle per order.
                # The serializer has discount_amount. If provided, we might need to split it? 
                # For simplicity, let's apply the discount only if it's a single order, or ignore it for multi-workspace.
                # Or better, let's assume the frontend calculates discounts per booking/order.
                
                tax_amount = sum(b.tax_amount for b in workspace_bookings)
                total_amount = subtotal - discount_amount + tax_amount
                
                # Create order
                order = Order.objects.create(
                    workspace_id=workspace_id,
                    user=request.user,
                    subtotal=subtotal,
                    discount_amount=discount_amount,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    notes=serializer.validated_data.get('notes', '')
                )
                
                # Add bookings to order
                order.bookings.set(workspace_bookings)
                created_orders.append(order)
            
            # If only one order, return it as object (backward compatibility if needed, but better to return list or standard format)
            # The schema says 201: OrderSerializer. If we return a list, we break schema.
            # But we must support multiple orders.
            # Let's return a list if multiple, or single if one? No, consistent API is better.
            # But the user might expect a single object if they only booked one thing.
            # Let's return a wrapper object: { "orders": [...] }
            
            return Response({
                'success': True,
                'count': len(created_orders),
                'orders': OrderSerializer(created_orders, many=True).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ListOrdersView(APIView):
    """List user's orders"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List user orders",
        description="Get all orders for the authenticated user",
        tags=["Orders"],
        responses={
            200: OrderListSerializer(many=True),
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request):
        """List user's orders"""
        try:
            orders = Order.objects.filter(
                user=request.user
            ).prefetch_related('bookings', 'bookings__space', 'workspace').order_by('-created_at')
            
            # Pagination
            paginator = PageNumberPagination()
            paginator.page_size = 20
            paginated_orders = paginator.paginate_queryset(orders, request)
            
            serializer = OrderListSerializer(paginated_orders, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class OrderDetailView(APIView):
    """Get order details"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get order details",
        description="Get detailed information about an order",
        tags=["Orders"],
        responses={
            200: OrderSerializer,
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, order_id):
        """Get order details"""
        try:
            order = Order.objects.prefetch_related('bookings', 'bookings__space', 'workspace').get(
                id=order_id
            )
            
            # Check if user is owner or admin of the workspace
            if order.user != request.user:
                # Check if user is admin/manager of the order's workspace
                if not check_workspace_member(request.user, order.workspace, ['admin', 'manager']):
                    return Response(
                        {"detail": "You don't have permission to view this order"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class InitiatePaymentView(APIView):
    """Initiate payment for an order"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Initiate payment",
        description="Start payment process for an order",
        tags=["Payments"],
        request=InitiatePaymentSerializer,
        responses={
            200: {"type": "object", "properties": {
                "payment_url": {"type": "string"},
                "payment_id": {"type": "string"},
                "reference": {"type": "string"}
            }},
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request):
        """Initiate payment"""
        serializer = InitiatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order_id = serializer.validated_data['order_id']
            payment_method = serializer.validated_data['payment_method']
            email = serializer.validated_data.get('email', request.user.email)
            
            # Get order
            order = Order.objects.get(id=order_id, user=request.user)
            workspace = order.workspace
            
            # Check if order is not already paid
            if order.status in ['paid', 'completed']:
                return Response(
                    {"detail": "Order already paid"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                workspace=workspace,
                user=request.user,
                amount=order.total_amount,
                currency='NGN',
                payment_method=payment_method
            )
            
            # Initialize payment with gateway (e.g., Paystack)
            payment_url = None
            reference = payment.id
            
            if payment_method == 'paystack':
                payment_url = self._initialize_paystack_payment(
                    payment, email, order.order_number
                )
            elif payment_method == 'flutterwave':
                payment_url = self._initialize_flutterwave_payment(
                    payment, email, order.order_number
                )
            
            # Update payment with reference
            payment.gateway_transaction_id = str(reference)
            payment.status = 'processing'
            payment.save()
            
            return Response({
                "payment_url": payment_url,
                "payment_id": str(payment.id),
                "reference": str(reference),
                "amount": str(payment.amount),
                "currency": payment.currency
            }, status=status.HTTP_200_OK)
        
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _initialize_paystack_payment(self, payment, email, order_number):
        """Initialize Paystack payment"""
        try:
            gateway = PaystackGateway()
            
            metadata = {
                "order_number": order_number,
                "workspace_id": str(payment.workspace_id),
                "payment_id": str(payment.id)
            }
            
            result = gateway.initialize_transaction(
                email=email,
                amount=payment.amount,
                reference=str(payment.id),
                metadata=metadata
            )
            
            if result['success']:
                return result['authorization_url']
            else:
                raise Exception(result.get('error', 'Paystack initialization failed'))
        except Exception as e:
            logger.error(f"Paystack initialization failed: {str(e)}")
            raise Exception(f"Paystack initialization failed: {str(e)}")
    
    def _initialize_flutterwave_payment(self, payment, email, order_number):
        """Initialize Flutterwave payment"""
        try:
            gateway = FlutterwaveGateway()
            
            metadata = {
                "order_number": order_number,
                "description": f"Payment for booking order {order_number}"
            }
            
            result = gateway.initialize_transaction(
                email=email,
                amount=payment.amount,
                tx_ref=str(payment.id),
                metadata=metadata
            )
            
            if result['success']:
                return result['payment_link']
            else:
                raise Exception(result.get('error', 'Flutterwave initialization failed'))
        except Exception as e:
            logger.error(f"Flutterwave initialization failed: {str(e)}")
            raise Exception(f"Flutterwave initialization failed: {str(e)}")


class PaymentWebhookView(APIView):
    """Handle payment gateway webhooks (server-to-server from Paystack/Flutterwave)"""
    permission_classes = []  # Public endpoint - Paystack will call this
    
    @extend_schema(
        summary="Payment webhook (Paystack → Your Server)",
        description="Handle payment gateway webhook. This is called by Paystack/Flutterwave servers, not by users.",
        tags=["Payments - Webhooks"],
        request=PaymentCallbackSerializer,
        responses={
            200: {"type": "object", "properties": {"status": {"type": "string"}}},
            400: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request):
        """Handle payment webhook from Paystack or Flutterwave"""
        try:
            from payment.webhooks import handle_webhook
            
            # Determine payment method from URL query param
            payment_method = request.query_params.get('method', 'paystack')
            
            # Get signature header for verification
            signature_header = None
            if payment_method == 'paystack':
                signature_header = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
            elif payment_method == 'flutterwave':
                signature_header = request.META.get('HTTP_VERIFI_HASH')
            
            logger.info(f"Received {payment_method} webhook")
            
            # Process webhook
            result = handle_webhook(
                request.data,
                payment_method=payment_method,
                signature_header=signature_header
            )
            
            if result['success']:
                return Response(
                    {
                        "status": "success",
                        "message": result.get('message', 'Webhook processed successfully')
                    },
                    status=status.HTTP_200_OK
                )
            else:
                logger.warning(f"Webhook processing failed: {result.get('error')}")
                return Response(
                    {
                        "status": "error",
                        "message": result.get('error', 'Webhook processing failed')
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentCallbackView(APIView):
    """Handle payment callback (user redirect from Paystack/Flutterwave)"""
    permission_classes = [IsAuthenticated]  # User must be logged in
    
    @extend_schema(
        summary="Payment callback (User Redirect)",
        description="Verify payment after user is redirected back from payment gateway. Your frontend should call this endpoint.",
        tags=["Payments - Callback"],
        parameters=[
            {
                "name": "reference",
                "in": "query",
                "required": True,
                "schema": {"type": "string"},
                "description": "Payment reference/transaction ID"
            }
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "payment": {"type": "object"},
                    "order": {"type": "object"}
                }
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
            403: {"type": "object", "properties": {"error": {"type": "string"}}},
            404: {"type": "object", "properties": {"error": {"type": "string"}}}
        }
    )
    def get(self, request):
        """Verify payment after user redirect from payment gateway"""
        try:
            reference = request.query_params.get('reference')
            
            if not reference:
                return Response(
                    {'error': 'Payment reference is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Payment callback for reference: {reference}")
            
            # Get payment by reference
            try:
                payment = Payment.objects.select_related('order', 'order__user').get(
                    gateway_transaction_id=reference
                )
            except Payment.DoesNotExist:
                return Response(
                    {'error': 'Payment not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if user owns this payment
            if payment.order.user != request.user:
                return Response(
                    {'error': 'You do not have permission to view this payment'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Verify payment with gateway API
            if payment.payment_method == 'paystack':
                from payment.gateways import PaystackGateway
                gateway = PaystackGateway()
            elif payment.payment_method == 'flutterwave':
                from payment.gateways import FlutterwaveGateway
                gateway = FlutterwaveGateway()
            else:
                return Response(
                    {'error': f'Unknown payment method: {payment.payment_method}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify transaction with payment gateway
            verify_result = gateway.verify_transaction(reference)
            
            if not verify_result['success']:
                return Response(
                    {
                        'success': False,
                        'error': 'Payment verification failed',
                        'details': verify_result.get('message', 'Unknown error')
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check payment status from gateway
            gateway_status = verify_result.get('status', '').lower()
            
            if gateway_status in ['success', 'successful']:
                # Payment successful - update if not already updated by webhook
                if payment.status != 'success':
                    payment.status = 'success'
                    payment.completed_at = timezone.now()
                    payment.save()
                    
                    # Update order
                    order = payment.order
                    if order.status != 'paid':
                        order.status = 'paid'
                        order.paid_at = timezone.now()
                        order.save()
                        
                        logger.info(f"Payment {payment.id} verified and updated via callback")
                
                return Response(
                    {
                        'success': True,
                        'message': 'Payment verified successfully',
                        'payment': {
                            'id': str(payment.id),
                            'reference': payment.gateway_transaction_id,
                            'amount': str(payment.amount),
                            'status': payment.status,
                            'payment_method': payment.payment_method
                        },
                        'order': {
                            'id': str(payment.order.id),
                            'order_number': payment.order.order_number,
                            'status': payment.order.status,
                            'total_amount': str(payment.order.total_amount)
                        }
                    },
                    status=status.HTTP_200_OK
                )
            else:
                # Payment failed or pending
                return Response(
                    {
                        'success': False,
                        'message': f'Payment status: {gateway_status}',
                        'payment': {
                            'id': str(payment.id),
                            'reference': payment.gateway_transaction_id,
                            'status': gateway_status
                        }
                    },
                    status=status.HTTP_200_OK
                )
        
        except Exception as e:
            logger.error(f"Payment callback error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ListPaymentsView(APIView):
    """List user's payments"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List payments",
        description="Get all payments for the authenticated user",
        tags=["Payments"],
        responses={
            200: PaymentListSerializer(many=True),
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request):
        """List user's payments"""
        try:
            payments = Payment.objects.filter(
                user=request.user
            ).select_related('order', 'workspace').order_by('-created_at')
            
            # Pagination
            from rest_framework.pagination import PageNumberPagination
            paginator = PageNumberPagination()
            paginator.page_size = 20
            paginated_payments = paginator.paginate_queryset(payments, request)
            
            serializer = PaymentListSerializer(paginated_payments, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class RequestRefundView(APIView):
    """Request refund for an order"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Request refund",
        description="Request refund for a completed order",
        tags=["Refunds"],
        request=CreateRefundSerializer,
        responses={
            201: RefundSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request):
        """Request refund"""
        serializer = CreateRefundSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order_id = serializer.validated_data['order_id']
            reason = serializer.validated_data['reason']
            reason_description = serializer.validated_data['reason_description']
            
            # Get order
            order = Order.objects.get(id=order_id, user=request.user)
            workspace = order.workspace
            
            # Check if order has payment
            if not hasattr(order, 'payment'):
                return Response(
                    {"detail": "Order has no payment to refund"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            payment = order.payment
            
            # Calculate refund amount
            refund_amount = serializer.validated_data.get('amount', payment.amount)
            
            if refund_amount > payment.amount:
                return Response(
                    {"detail": f"Refund amount cannot exceed payment amount ({payment.amount})"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create refund
            refund = Refund.objects.create(
                payment=payment,
                order=order,
                workspace=workspace,
                user=request.user,
                amount=refund_amount,
                reason=reason,
                reason_description=reason_description
            )
            
            return Response(
                RefundSerializer(refund).data,
                status=status.HTTP_201_CREATED
            )
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentStatusView(APIView):
    """Get payment status"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get payment status",
        description="Get detailed payment status",
        tags=["Payments"],
        responses={
            200: PaymentSerializer,
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, payment_id):
        """Get payment status"""
        try:
            payment = Payment.objects.select_related('order', 'workspace').get(id=payment_id)
            
            # Check if user is owner
            if payment.user != request.user:
                # Check if user is admin/manager of the workspace
                if not check_workspace_member(request.user, payment.workspace, ['admin', 'manager']):
                    return Response(
                        {"detail": "You don't have permission to view this payment"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
