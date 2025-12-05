"""
QR Code Views - Order QR code generation and retrieval
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import ScopedRateThrottle
from qr_code.models import OrderQRCode, BookingQRCode
from qr_code.serializers import OrderQRCodeSerializer, VerifyQRCodeSerializer, FileUploadSerializer, FileUploadResponseSerializer
from qr_code.tasks import generate_qr_code_for_order
from payment.models import Order
from booking.models import Booking
from workspace.permissions import check_workspace_member
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
from Xbooking.appwrite_storage import upload_file_to_appwrite
import logging

logger = logging.getLogger(__name__)


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


class GetBookingQRCodeView(APIView):
    """Get QR code for a booking"""
    permission_classes = [IsAuthenticated]
    serializer_class = None  # Will use BookingQRCodeSerializer
    
    @extend_schema(
        summary="Get booking QR code",
        description="Get QR code details for a booking",
        tags=["QR Codes - Bookings"],
        responses={
            200: {"type": "object"},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, booking_id):
        """Get booking QR code"""
        from qr_code.serializers import BookingQRCodeSerializer
        
        try:
            # Get the booking - user can only access their own bookings
            booking = Booking.objects.get(id=booking_id, user=request.user)
            workspace = booking.workspace
            
            try:
                qr_code = booking.qr_code
                serializer = BookingQRCodeSerializer(qr_code, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            except BookingQRCode.DoesNotExist:
                return Response(
                    {"detail": "QR code not generated yet for this booking"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class FileUploadView(APIView):
    """
    Unauthenticated file upload endpoint for frontend.
    Frontend must send the file_upload_key in headers or query params for authorization.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'file_upload'
    
    @extend_schema(
        summary="Upload file to cloud storage",
        description="Upload image or document to Appwrite cloud storage. Requires FILE_UPLOAD_KEY authorization.",
        tags=["File Upload"],
        request=FileUploadSerializer,
        responses={
            200: FileUploadResponseSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            401: {"type": "object", "properties": {"detail": {"type": "string"}}},
        }
    )
    def post(self, request):
        """Upload file to cloud storage"""
        try:
            # Get file_upload_key from headers or query params
            file_upload_key = request.headers.get('X-File-Upload-Key') or request.query_params.get('file_upload_key')
            
            # Validate file_upload_key
            if not file_upload_key:
                return Response(
                    {"detail": "Missing file_upload_key. Send it in X-File-Upload-Key header or file_upload_key query param."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            expected_key = settings.FILE_UPLOAD_KEY
            if not expected_key:
                logger.error("FILE_UPLOAD_KEY not configured in settings")
                return Response(
                    {"detail": "File upload is not configured on the server"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            if file_upload_key != expected_key:
                logger.warning(f"Invalid file_upload_key attempt: {file_upload_key[:10]}...")
                return Response(
                    {"detail": "Invalid file_upload_key"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Validate request data
            serializer = FileUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Get uploaded file
            file = serializer.validated_data['file']
            file_type = serializer.validated_data.get('file_type', 'other')
            
            # Read file content
            file_content = file.read()
            
            # Upload to Appwrite
            result = upload_file_to_appwrite(
                file_data=file_content,
                filename=file.name
            )
            
            if not result.get('success'):
                logger.error(f"File upload to Appwrite failed: {result.get('error')}")
                return Response(
                    {"detail": f"File upload failed: {result.get('error')}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Return success response
            response_data = {
                'success': True,
                'file_id': result.get('file_id'),
                'file_url': result.get('file_url'),
                'filename': result.get('filename'),
                'size': result.get('size', file.size),
                'message': 'File uploaded successfully'
            }
            
            response_serializer = FileUploadResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            return Response(
                {"detail": f"File upload error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )