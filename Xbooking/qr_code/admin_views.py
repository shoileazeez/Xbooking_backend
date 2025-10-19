"""
Admin views for QR code verification and management
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from qr_code.models import OrderQRCode, QRCodeScanLog
from qr_code.serializers import OrderQRCodeSerializer, QRCodeScanLogSerializer, VerifyQRCodeSerializer
from payment.models import Order
from booking.models import Booking
from workspace.permissions import check_workspace_member
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.db.models import Count


class AdminQRCodeDashboardView(APIView):
    """Admin dashboard for QR code verification"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="QR code verification dashboard",
        description="Get QR code statistics and pending verifications",
        tags=["Admin QR Verification"],
        responses={
            200: {"type": "object", "properties": {
                "pending_verifications": {"type": "integer"},
                "verified_today": {"type": "integer"},
                "total_scanned": {"type": "integer"},
                "expired_codes": {"type": "integer"},
                "recent_scans": {"type": "array"}
            }},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id):
        """Get QR code dashboard"""
        # Only staff/manager/admin can access
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get statistics
            pending = OrderQRCode.objects.filter(
                order__workspace_id=workspace_id,
                status='scanned',
                verified=False
            ).count()
            
            verified_today = OrderQRCode.objects.filter(
                order__workspace_id=workspace_id,
                verified=True,
                verified_at__date=timezone.now().date()
            ).count()
            
            total_scanned = QRCodeScanLog.objects.filter(
                qr_code__order__workspace_id=workspace_id
            ).count()
            
            expired = OrderQRCode.objects.filter(
                order__workspace_id=workspace_id,
                status='expired'
            ).count()
            
            # Get recent scans
            recent_scans = QRCodeScanLog.objects.filter(
                qr_code__order__workspace_id=workspace_id
            ).select_related('scanned_by', 'qr_code__order').order_by('-scanned_at')[:10]
            
            recent_scans_data = []
            for scan in recent_scans:
                recent_scans_data.append({
                    'verification_code': scan.qr_code.verification_code,
                    'order_number': scan.qr_code.order.order_number,
                    'scanned_by': scan.scanned_by.email,
                    'scan_result': scan.scan_result,
                    'scanned_at': scan.scanned_at
                })
            
            return Response({
                'pending_verifications': pending,
                'verified_today': verified_today,
                'total_scanned': total_scanned,
                'expired_codes': expired,
                'recent_scans': recent_scans_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminListPendingVerificationsView(APIView):
    """List pending QR code verifications"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List pending verifications",
        description="Get all pending QR codes waiting for verification",
        tags=["Admin QR Verification"],
        responses={
            200: {"type": "array", "items": {"type": "object"}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id):
        """List pending verifications"""
        # Only staff/manager/admin can access
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get pending QR codes (scanned but not verified)
            pending_qrs = OrderQRCode.objects.filter(
                order__workspace_id=workspace_id,
                status='scanned',
                verified=False
            ).select_related('order', 'order__user').order_by('-last_scanned_at')
            
            pending_data = []
            for qr in pending_qrs:
                pending_data.append({
                    'id': str(qr.id),
                    'verification_code': qr.verification_code,
                    'order_number': qr.order.order_number,
                    'user_email': qr.order.user.email,
                    'user_name': qr.order.user.first_name or qr.order.user.email,
                    'total_amount': str(qr.order.total_amount),
                    'bookings_count': qr.order.bookings.count(),
                    'scan_count': qr.scan_count,
                    'last_scanned_at': qr.last_scanned_at,
                    'scanned_by_ip': qr.scanned_by_ip,
                    'expires_at': qr.expires_at,
                    'time_remaining': self._get_time_remaining(qr.expires_at)
                })
            
            return Response(pending_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_time_remaining(self, expires_at):
        """Calculate time remaining for expiry"""
        if not expires_at:
            return None
        
        remaining = expires_at - timezone.now()
        if remaining.total_seconds() <= 0:
            return "Expired"
        
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


class AdminVerifyQRCodeView(APIView):
    """Admin verify QR code and complete check-in"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Verify QR code (Admin)",
        description="Admin verifies QR code and completes check-in",
        tags=["Admin QR Verification"],
        request={"type": "object", "properties": {
            "qr_code_id": {"type": "string"},
            "notes": {"type": "string"}
        }},
        responses={
            200: OrderQRCodeSerializer(),
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request, workspace_id):
        """Verify QR code"""
        # Only staff/manager/admin can verify
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to verify QR codes"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            qr_code_id = request.data.get('qr_code_id')
            notes = request.data.get('notes', '')
            
            if not qr_code_id:
                return Response(
                    {"detail": "qr_code_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get QR code
            qr_code = OrderQRCode.objects.get(
                id=qr_code_id,
                order__workspace_id=workspace_id
            )
            
            # Check if already verified
            if qr_code.verified:
                return Response(
                    {
                        "detail": "QR code already verified",
                        "verified_at": qr_code.verified_at,
                        "verified_by": qr_code.verified_by.email if qr_code.verified_by else None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if expired
            if qr_code.expires_at and timezone.now() > qr_code.expires_at:
                qr_code.status = 'expired'
                qr_code.save()
                
                return Response(
                    {"detail": "QR code has expired"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify QR code
            qr_code.verified = True
            qr_code.verified_at = timezone.now()
            qr_code.verified_by = request.user
            qr_code.status = 'verified'
            qr_code.save()
            
            # Update all bookings to in_progress
            order = qr_code.order
            bookings = order.bookings.filter(status='confirmed')
            updated_count = bookings.update(status='in_progress')
            
            return Response({
                'qr_code': OrderQRCodeSerializer(qr_code, context={'request': request}).data,
                'bookings_updated': updated_count,
                'message': f'QR code verified successfully. {updated_count} booking(s) marked as in-progress.'
            }, status=status.HTTP_200_OK)
        except OrderQRCode.DoesNotExist:
            return Response(
                {"detail": "QR code not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminRejectQRCodeView(APIView):
    """Admin reject QR code verification"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Reject QR code",
        description="Admin rejects QR code and marks as invalid",
        tags=["Admin QR Verification"],
        request={"type": "object", "properties": {
            "qr_code_id": {"type": "string"},
            "reason": {"type": "string"}
        }},
        responses={
            200: OrderQRCodeSerializer(),
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request, workspace_id):
        """Reject QR code"""
        # Only staff/manager/admin can reject
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to reject QR codes"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            qr_code_id = request.data.get('qr_code_id')
            reason = request.data.get('reason', 'No reason provided')
            
            if not qr_code_id:
                return Response(
                    {"detail": "qr_code_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get QR code
            qr_code = OrderQRCode.objects.get(
                id=qr_code_id,
                order__workspace_id=workspace_id
            )
            
            # Mark as invalid (revert to sent)
            qr_code.status = 'sent'
            qr_code.save()
            
            # Log rejection notification
            from notifications.models import Notification
            Notification.objects.create(
                user=qr_code.order.user,
                notification_type='qr_code_generated',
                channel='email',
                title='QR Code Verification Failed',
                message=f'QR code for order {qr_code.order.order_number} was rejected: {reason}',
                is_sent=True,
                sent_at=timezone.now(),
                data={
                    'qr_code_id': str(qr_code.id),
                    'reason': reason
                }
            )
            
            return Response({
                'qr_code': OrderQRCodeSerializer(qr_code, context={'request': request}).data,
                'message': 'QR code rejected and reverted to sent status. User notified.',
                'reason': reason
            }, status=status.HTTP_200_OK)
        except OrderQRCode.DoesNotExist:
            return Response(
                {"detail": "QR code not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminQRCodeDetailsView(APIView):
    """Get detailed QR code information"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get QR code details",
        description="Get detailed information about a QR code including scan history",
        tags=["Admin QR Verification"],
        responses={
            200: {"type": "object", "properties": {
                "qr_code": OrderQRCodeSerializer(),
                "scan_history": {"type": "array"},
                "order_details": {"type": "object"},
                "bookings": {"type": "array"}
            }},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id, qr_code_id):
        """Get QR code details"""
        # Only staff/manager/admin can access
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            qr_code = OrderQRCode.objects.get(
                id=qr_code_id,
                order__workspace_id=workspace_id
            )
            
            # Get scan history
            scans = QRCodeScanLog.objects.filter(qr_code=qr_code).select_related('scanned_by').order_by('-scanned_at')
            
            scan_history = []
            for scan in scans:
                scan_history.append({
                    'scanned_at': scan.scanned_at,
                    'scanned_by': scan.scanned_by.email,
                    'scan_device_ip': scan.scan_device_ip,
                    'scan_result': scan.scan_result
                })
            
            # Get order details
            order = qr_code.order
            
            # Get bookings
            bookings_data = []
            for booking in order.bookings.all():
                bookings_data.append({
                    'id': str(booking.id),
                    'space_name': booking.space.name,
                    'check_in': booking.check_in,
                    'check_out': booking.check_out,
                    'status': booking.status,
                    'total_price': str(booking.total_price)
                })
            
            return Response({
                'qr_code': OrderQRCodeSerializer(qr_code, context={'request': request}).data,
                'scan_history': scan_history,
                'order_details': {
                    'order_number': order.order_number,
                    'user_email': order.user.email,
                    'user_name': order.user.first_name or order.user.email,
                    'total_amount': str(order.total_amount),
                    'status': order.status,
                    'created_at': order.created_at,
                    'paid_at': order.paid_at
                },
                'bookings': bookings_data
            }, status=status.HTTP_200_OK)
        except OrderQRCode.DoesNotExist:
            return Response(
                {"detail": "QR code not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminVerificationStatsView(APIView):
    """Get verification statistics"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get verification statistics",
        description="Get QR code verification statistics",
        tags=["Admin QR Verification"],
        responses={
            200: {"type": "object", "properties": {
                "total_qr_codes": {"type": "integer"},
                "verified": {"type": "integer"},
                "pending": {"type": "integer"},
                "expired": {"type": "integer"},
                "by_status": {"type": "object"},
                "today_stats": {"type": "object"}
            }},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id):
        """Get verification statistics"""
        # Only staff/manager/admin can access
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            qr_codes = OrderQRCode.objects.filter(order__workspace_id=workspace_id)
            
            # Overall stats
            total = qr_codes.count()
            verified = qr_codes.filter(verified=True).count()
            pending = qr_codes.filter(status='scanned', verified=False).count()
            expired = qr_codes.filter(status='expired').count()
            
            # By status
            by_status = qr_codes.values('status').annotate(count=Count('id'))
            status_dict = {item['status']: item['count'] for item in by_status}
            
            # Today's stats
            today = timezone.now().date()
            today_generated = qr_codes.filter(created_at__date=today).count()
            today_verified = qr_codes.filter(verified_at__date=today).count()
            today_scans = QRCodeScanLog.objects.filter(
                qr_code__order__workspace_id=workspace_id,
                scanned_at__date=today
            ).count()
            
            return Response({
                'total_qr_codes': total,
                'verified': verified,
                'pending': pending,
                'expired': expired,
                'by_status': status_dict,
                'today_stats': {
                    'generated': today_generated,
                    'verified': today_verified,
                    'scans': today_scans,
                    'verification_rate': f"{(today_verified/today_generated*100) if today_generated > 0 else 0:.1f}%"
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminResendQRCodeView(APIView):
    """Resend QR code to user"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Resend QR code",
        description="Resend QR code email to user",
        tags=["Admin QR Verification"],
        responses={
            200: {"type": "object", "properties": {
                "message": {"type": "string"}
            }},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request, workspace_id, qr_code_id):
        """Resend QR code"""
        # Only staff/manager/admin can resend
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to resend QR codes"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            qr_code = OrderQRCode.objects.get(
                id=qr_code_id,
                order__workspace_id=workspace_id
            )
            
            # Trigger email send
            from qr_code.tasks import send_qr_code_email
            send_qr_code_email.delay(str(qr_code.order.id), str(qr_code.id))
            
            return Response({
                'message': f'QR code will be resent to {qr_code.order.user.email}'
            }, status=status.HTTP_200_OK)
        except OrderQRCode.DoesNotExist:
            return Response(
                {"detail": "QR code not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
