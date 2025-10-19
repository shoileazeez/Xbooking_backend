"""
Payment and Order Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
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


# Import Celery tasks
from qr_code.tasks import (
    generate_qr_code_for_order, send_qr_code_email,
    send_order_confirmation_email, send_payment_confirmation_email
)


class CreateOrderView(APIView):
    """Create order from bookings"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Create order from bookings",
        description="Create an order from one or more bookings",
        tags=["Orders"],
        request=CreateOrderSerializer(),
        responses={
            201: OrderSerializer(),
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request, workspace_id):
        """Create a new order"""
        # Check workspace membership
        if not check_workspace_member(request.user, workspace_id, ['user', 'staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            booking_ids = serializer.validated_data['booking_ids']
            bookings = Booking.objects.filter(
                id__in=booking_ids,
                workspace_id=workspace_id,
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
            
            # Calculate totals
            subtotal = sum(b.base_price for b in bookings)
            discount_amount = serializer.validated_data.get('discount_amount', Decimal('0'))
            tax_amount = sum(b.tax_amount for b in bookings)
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
            order.bookings.set(bookings)
            
            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_201_CREATED
            )
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
    def get(self, request, workspace_id):
        """List user's orders"""
        if not check_workspace_member(request.user, workspace_id, ['user', 'staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            orders = Order.objects.filter(
                workspace_id=workspace_id,
                user=request.user
            ).prefetch_related('bookings').order_by('-created_at')
            
            serializer = OrderListSerializer(orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
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
            200: OrderSerializer(),
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id, order_id):
        """Get order details"""
        if not check_workspace_member(request.user, workspace_id, ['user', 'staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            order = Order.objects.prefetch_related('bookings').get(
                id=order_id,
                workspace_id=workspace_id
            )
            
            # Check if user is owner or admin
            if order.user != request.user and not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
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
        request=InitiatePaymentSerializer(),
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
    def post(self, request, workspace_id):
        """Initiate payment"""
        if not check_workspace_member(request.user, workspace_id, ['user', 'staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InitiatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order_id = serializer.validated_data['order_id']
            payment_method = serializer.validated_data['payment_method']
            email = serializer.validated_data.get('email', request.user.email)
            
            # Get order
            order = Order.objects.get(id=order_id, workspace_id=workspace_id, user=request.user)
            
            # Check if order is not already paid
            if order.status in ['paid', 'completed']:
                return Response(
                    {"detail": "Order already paid"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                workspace_id=workspace_id,
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
            paystack_key = "YOUR_PAYSTACK_SECRET_KEY"  # Use settings
            headers = {
                "Authorization": f"Bearer {paystack_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "email": email,
                "amount": int(payment.amount * 100),  # Paystack uses kobo
                "reference": str(payment.id),
                "metadata": {
                    "order_number": order_number,
                    "workspace_id": str(payment.workspace_id)
                }
            }
            
            # This is a placeholder - implement actual Paystack integration
            # response = requests.post(
            #     "https://api.paystack.co/transaction/initialize",
            #     json=data,
            #     headers=headers
            # )
            # if response.status_code == 200:
            #     return response.json()['data']['authorization_url']
            
            return f"https://checkout.paystack.com/test_reference_{payment.id}"
        except Exception as e:
            raise Exception(f"Paystack initialization failed: {str(e)}")
    
    def _initialize_flutterwave_payment(self, payment, email, order_number):
        """Initialize Flutterwave payment"""
        try:
            flutterwave_key = "YOUR_FLUTTERWAVE_SECRET_KEY"  # Use settings
            
            data = {
                "tx_ref": str(payment.id),
                "amount": str(payment.amount),
                "currency": "NGN",
                "customer": {
                    "email": email
                },
                "customizations": {
                    "title": f"Order {order_number}",
                    "description": f"Payment for booking order"
                }
            }
            
            # This is a placeholder - implement actual Flutterwave integration
            # headers = {"Authorization": f"Bearer {flutterwave_key}"}
            # response = requests.post(
            #     "https://api.flutterwave.com/v3/payments",
            #     json=data,
            #     headers=headers
            # )
            
            return f"https://checkout.flutterwave.com/test_reference_{payment.id}"
        except Exception as e:
            raise Exception(f"Flutterwave initialization failed: {str(e)}")


class PaymentCallbackView(APIView):
    """Handle payment gateway callbacks"""
    permission_classes = []  # Public endpoint for webhook
    
    @extend_schema(
        summary="Payment callback",
        description="Handle payment gateway callback (webhook)",
        tags=["Payments"],
        request=PaymentCallbackSerializer(),
        responses={
            200: {"type": "object", "properties": {"status": {"type": "string"}}},
            400: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request):
        """Handle payment callback"""
        try:
            reference = request.data.get('reference')
            
            if not reference:
                return Response(
                    {"detail": "Reference is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get payment
            payment = Payment.objects.get(gateway_transaction_id=str(reference))
            
            # Verify payment status from gateway
            payment_status = request.data.get('status', 'failed')
            
            if payment_status == 'success':
                # Update payment
                payment.status = 'success'
                payment.completed_at = timezone.now()
                payment.save()
                
                # Update order
                order = payment.order
                order.status = 'paid'
                order.payment_method = payment.payment_method
                order.payment_reference = str(reference)
                order.paid_at = timezone.now()
                order.save()
                
                # Update bookings to confirmed
                for booking in order.bookings.all():
                    booking.status = 'confirmed'
                    booking.confirmed_at = timezone.now()
                    booking.save()
                
                # Trigger background tasks
                send_payment_confirmation_email.delay(str(order.id))
                generate_qr_code_for_order.delay(str(order.id))
                
                return Response(
                    {
                        "status": "success",
                        "message": "Payment processed successfully",
                        "detail": "QR code will be sent to user email shortly"
                    },
                    status=status.HTTP_200_OK
                )
            else:
                payment.status = 'failed'
                payment.save()
                
                return Response(
                    {"status": "failed", "message": "Payment failed"},
                    status=status.HTTP_200_OK
                )
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
    def get(self, request, workspace_id):
        """List user's payments"""
        if not check_workspace_member(request.user, workspace_id, ['user', 'staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            payments = Payment.objects.filter(
                workspace_id=workspace_id,
                user=request.user
            ).select_related('order').order_by('-created_at')
            
            serializer = PaymentListSerializer(payments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
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
        request=CreateRefundSerializer(),
        responses={
            201: RefundSerializer(),
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request, workspace_id):
        """Request refund"""
        if not check_workspace_member(request.user, workspace_id, ['user', 'staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreateRefundSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order_id = serializer.validated_data['order_id']
            reason = serializer.validated_data['reason']
            reason_description = serializer.validated_data['reason_description']
            
            # Get order
            order = Order.objects.get(id=order_id, workspace_id=workspace_id, user=request.user)
            
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
                workspace_id=workspace_id,
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
            200: PaymentSerializer(),
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id, payment_id):
        """Get payment status"""
        if not check_workspace_member(request.user, workspace_id, ['user', 'staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            payment = Payment.objects.select_related('order').get(
                id=payment_id,
                workspace_id=workspace_id
            )
            
            # Check if user is owner
            if payment.user != request.user:
                if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
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
