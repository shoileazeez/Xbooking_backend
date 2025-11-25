"""
QR Code Views - Order QR code generation and retrieval
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from qr_code.models import OrderQRCode
from qr_code.serializers import OrderQRCodeSerializer, VerifyQRCodeSerializer
from qr_code.tasks import generate_qr_code_for_order
from payment.models import Order
from booking.models import Booking
from workspace.permissions import check_workspace_member
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.db.models import Q


class GenerateOrderQRCodeView(APIView):
    """Generate QR code for order"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'sensitive_action'
    serializer_class = OrderQRCodeSerializer
    
    @extend_schema(
        summary="Generate QR code for order",
        description="Generate and send QR code to user",
        tags=["QR Codes"],
        responses={
            200: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request, order_id):
        """Generate QR code for order"""
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            workspace = order.workspace
            
            if not check_workspace_member(request.user, workspace, ['user', 'staff', 'manager', 'admin']):
                return Response(
                    {"detail": "You don't have permission to access this workspace"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if order is paid
            if order.status not in ['paid', 'processing', 'completed']:
                return Response(
                    {"detail": "QR code can only be generated for paid orders"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Trigger QR code generation in background
            generate_qr_code_for_order.delay(str(order.id))
            
            return Response(
                {"detail": "QR code generation started. You will receive it via email shortly."},
                status=status.HTTP_200_OK
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


class GetOrderQRCodeView(APIView):
    """Get QR code for an order"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderQRCodeSerializer
    
    @extend_schema(
        summary="Get order QR code",
        description="Get QR code details for an order",
        tags=["QR Codes"],
        responses={
            200: OrderQRCodeSerializer,
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, order_id):
        """Get order QR code"""
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            workspace = order.workspace
            
            if not check_workspace_member(request.user, workspace, ['user', 'staff', 'manager', 'admin']):
                return Response(
                    {"detail": "You don't have permission to access this workspace"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            try:
                qr_code = order.qr_code
                serializer = OrderQRCodeSerializer(qr_code, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            except OrderQRCode.DoesNotExist:
                return Response(
                    {"detail": "QR code not generated yet"},
                    status=status.HTTP_404_NOT_FOUND
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