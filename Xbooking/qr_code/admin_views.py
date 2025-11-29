"""
Admin views for QR code verification and check-in/check-out management
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from qr_code.models import BookingQRCode, CheckIn
from .serializers import BookingQRCodeSerializer, CheckInSerializer
from booking.models import Booking
from workspace.permissions import check_workspace_member
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta


class AdminCheckInView(APIView):
    """Admin check-in a guest using QR code"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Check-in guest via QR code",
        description="Admin scans QR code to check-in a guest. Send verification_code and booking_id.",
        tags=["Admin Check-in/Check-out"],
        request={"type": "object", "properties": {
            "verification_code": {"type": "string", "description": "Verification code from QR code (BKG-XXXXX)"},
            "booking_id": {"type": "string", "description": "Booking UUID"},
            "notes": {"type": "string", "description": "Optional check-in notes"}
        }},
        responses={
            200: {"type": "object", "properties": {
                "message": {"type": "string"},
                "check_in": {"type": "object"},
                "booking": {"type": "object"}
            }},
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request, workspace_id):
        """Check-in guest using verification_code and booking_id"""
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to verify QR codes"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            verification_code = request.data.get('verification_code')
            booking_id = request.data.get('booking_id')
            notes = request.data.get('notes', '')
            
            if not verification_code or not booking_id:
                return Response(
                    {"detail": "verification_code and booking_id are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get BookingQRCode using verification_code and booking_id for validation
            qr_code = BookingQRCode.objects.select_related('booking').get(
                verification_code=verification_code,
                booking_id=booking_id,
                booking__workspace_id=workspace_id
            )
            
            booking = qr_code.booking
            
            # Check if already checked in
            if booking.is_checked_in:
                return Response(
                    {
                        "detail": "Guest is already checked in",
                        "checked_in_at": booking.check_in
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate check-in time (can only check-in at or after scheduled check-in time)
            now = timezone.now()
            if now < booking.check_in:
                time_diff = booking.check_in - now
                minutes = int(time_diff.total_seconds() / 60)
                return Response(
                    {
                        "detail": f"Check-in not available yet. Available in {minutes} minutes.",
                        "check_in_time": booking.check_in
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if booking is within valid time window (not expired)
            if now > booking.check_out:
                return Response(
                    {
                        "detail": "Booking period has expired",
                        "check_out_time": booking.check_out
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create CheckIn record
            check_in_obj = CheckIn.objects.create(
                booking=booking,
                qr_code=qr_code,
                check_in_time=now,
                verified_by=request.user,
                notes=notes
            )
            
            # Update Booking status
            booking.is_checked_in = True
            booking.status = 'in_progress'
            booking.save()
            
            # Update QR code status and counters
            qr_code.total_check_ins += 1
            qr_code.scan_count += 1
            qr_code.last_scanned_at = now
            qr_code.scanned_by_ip = self._get_client_ip(request)
            qr_code.status = 'verified'
            qr_code.save()
            
            return Response({
                'message': 'Guest checked in successfully',
                'check_in': CheckInSerializer(check_in_obj).data,
                'booking': {
                    'id': str(booking.id),
                    'space': booking.space.name,
                    'check_in': booking.check_in,
                    'check_out': booking.check_out,
                    'status': booking.status
                },
                'qr_code_stats': {
                    'scan_count': qr_code.scan_count,
                    'total_check_ins': qr_code.total_check_ins,
                    'max_check_ins': qr_code.max_check_ins or qr_code.calculate_max_check_ins()
                }
            }, status=status.HTTP_200_OK)
            
        except BookingQRCode.DoesNotExist:
            return Response(
                {"detail": "QR code not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_client_ip(self, request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminCheckOutView(APIView):
    """Admin check-out a guest using QR code"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Check-out guest via QR code",
        description="Admin scans QR code to check-out a guest. Send verification_code and booking_id.",
        tags=["Admin Check-in/Check-out"],
        request={"type": "object", "properties": {
            "verification_code": {"type": "string", "description": "Verification code from QR code (BKG-XXXXX)"},
            "booking_id": {"type": "string", "description": "Booking UUID"},
            "notes": {"type": "string", "description": "Optional check-out notes"}
        }},
        responses={
            200: {"type": "object", "properties": {
                "message": {"type": "string"},
                "check_in": {"type": "object"},
                "booking": {"type": "object"},
                "duration": {"type": "string"}
            }},
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request, workspace_id):
        """Check-out guest using verification_code and booking_id"""
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to verify QR codes"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            verification_code = request.data.get('verification_code')
            booking_id = request.data.get('booking_id')
            notes = request.data.get('notes', '')
            
            if not verification_code or not booking_id:
                return Response(
                    {"detail": "verification_code and booking_id are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get BookingQRCode using verification_code and booking_id for validation
            qr_code = BookingQRCode.objects.select_related('booking').get(
                verification_code=verification_code,
                booking_id=booking_id,
                booking__workspace_id=workspace_id
            )
            
            booking = qr_code.booking
            
            # Get or create CheckIn record
            check_in_obj = CheckIn.objects.filter(
                booking=booking,
                qr_code=qr_code,
                check_out_time__isnull=True  # Not yet checked out
            ).first()
            
            if not check_in_obj:
                # Create new CheckIn if doesn't exist
                check_in_obj = CheckIn.objects.create(
                    booking=booking,
                    qr_code=qr_code,
                    check_in_time=timezone.now(),
                    check_out_time=timezone.now(),
                    verified_by=request.user,
                    notes=notes
                )
            else:
                # Update existing CheckIn with checkout time
                check_in_obj.check_out_time = timezone.now()
                check_in_obj.notes = notes
                check_in_obj.save()
            
            # Update Booking status
            booking.is_checked_out = True
            booking.status = 'completed'
            booking.save()
            
            # For monthly bookings, don't mark QR as used yet
            if booking.booking_type != 'monthly':
                qr_code.used = True
            
            # Update QR code counters
            qr_code.scan_count += 1
            qr_code.last_scanned_at = timezone.now()
            qr_code.scanned_by_ip = self._get_client_ip(request)
            qr_code.status = 'verified'
            qr_code.save()
            
            # Calculate duration
            duration = check_in_obj.check_out_time - check_in_obj.check_in_time
            duration_str = f"{int(duration.total_seconds() // 3600)}h {int((duration.total_seconds() % 3600) // 60)}m"
            
            return Response({
                'message': 'Guest checked out successfully',
                'check_in': CheckInSerializer(check_in_obj).data,
                'booking': {
                    'id': str(booking.id),
                    'space': booking.space.name,
                    'check_in': booking.check_in,
                    'check_out': booking.check_out,
                    'status': booking.status
                },
                'duration': duration_str,
                'qr_code_stats': {
                    'scan_count': qr_code.scan_count,
                    'total_check_ins': qr_code.total_check_ins,
                    'max_check_ins': qr_code.max_check_ins or qr_code.calculate_max_check_ins()
                }
            }, status=status.HTTP_200_OK)
            
        except BookingQRCode.DoesNotExist:
            return Response(
                {"detail": "QR code not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_client_ip(self, request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminCheckInListView(APIView):
    """List check-ins for a workspace"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List check-ins",
        description="Get all check-ins for workspace",
        tags=["Admin Check-in/Check-out"],
        responses={
            200: {"type": "array", "items": {"type": "object"}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id):
        """List check-ins"""
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get today's check-ins
            today = timezone.now().date()
            check_ins = CheckIn.objects.filter(
                booking__workspace_id=workspace_id,
                check_in_time__date=today
            ).select_related('booking', 'booking__space', 'verified_by').order_by('-check_in_time')
            
            data = []
            for check_in in check_ins:
                booking = check_in.booking
                data.append({
                    'id': str(check_in.id),
                    'booking_id': str(booking.id),
                    'space': booking.space.name,
                    'guest_name': booking.user.full_name or booking.user.email,
                    'check_in_time': check_in.check_in_time,
                    'check_out_time': check_in.check_out_time,
                    'status': 'checked_out' if check_in.check_out_time else 'checked_in',
                    'verified_by': check_in.verified_by.email,
                    'notes': check_in.notes
                })
            
            return Response({
                'date': today.isoformat(),
                'total_check_ins': len(data),
                'check_ins': data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminQRCodeDashboardView(APIView):
    """Admin dashboard for QR code verification"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="QR code verification dashboard",
        description="Get QR code statistics and pending check-ins",
        tags=["Admin Check-in/Check-out"],
        responses={
            200: {"type": "object", "properties": {
                "pending_check_ins": {"type": "integer"},
                "checked_in_today": {"type": "integer"},
                "checked_out_today": {"type": "integer"},
                "active_bookings": {"type": "integer"},
                "recent_check_ins": {"type": "array"}
            }},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id):
        """Get QR code dashboard"""
        if not check_workspace_member(request.user, workspace_id, ['staff', 'manager', 'admin']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            today = timezone.now().date()
            now = timezone.now()
            
            # Get statistics
            pending_check_ins = Booking.objects.filter(
                workspace_id=workspace_id,
                is_checked_in=False,
                check_in__lte=now,
                check_out__gte=now
            ).count()
            
            checked_in_today = CheckIn.objects.filter(
                booking__workspace_id=workspace_id,
                check_in_time__date=today
            ).count()
            
            checked_out_today = CheckIn.objects.filter(
                booking__workspace_id=workspace_id,
                check_out_time__date=today,
                check_out_time__isnull=False
            ).count()
            
            active_bookings = Booking.objects.filter(
                workspace_id=workspace_id,
                status='in_progress'
            ).count()
            
            # Get recent check-ins
            recent_check_ins = CheckIn.objects.filter(
                booking__workspace_id=workspace_id
            ).select_related('booking', 'booking__space', 'verified_by').order_by('-check_in_time')[:10]
            
            recent_data = []
            for check_in in recent_check_ins:
                booking = check_in.booking
                recent_data.append({
                    'booking_id': str(booking.id),
                    'space': booking.space.name,
                    'guest': booking.user.email,
                    'check_in_time': check_in.check_in_time,
                    'status': 'checked_out' if check_in.check_out_time else 'checked_in'
                })
            
            return Response({
                'pending_check_ins': pending_check_ins,
                'checked_in_today': checked_in_today,
                'checked_out_today': checked_out_today,
                'active_bookings': active_bookings,
                'recent_check_ins': recent_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
