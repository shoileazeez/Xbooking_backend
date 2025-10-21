"""
Admin views for managing guest verifications per booking
Allows admins/managers to verify or reject guests before QR code is sent
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction

from workspace.models import Workspace, WorkspaceUser
from booking.models import Booking, Guest
from booking.serializers import GuestSerializer
from booking.admin_guest_serializers import (
    AdminVerifyGuestSerializer,
    AdminRejectGuestSerializer,
    AdminGuestListSerializer,
)
from workspace.permissions import check_workspace_member
from notifications.tasks import send_notification
from booking.guest_tasks import send_guest_qr_code_email


class AdminListPendingGuestsForBookingView(APIView):
    """List all pending guests for a specific booking"""
    permission_classes = [IsAuthenticated]
    serializer_class = AdminGuestListSerializer
    
    def get(self, request, workspace_id, booking_id):
        """
        GET /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/pending-guests/
        
        List all guests pending admin verification for this booking
        """
        # Check permission
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {'error': 'Only admins/managers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Verify booking exists
            booking = Booking.objects.get(id=booking_id, workspace_id=workspace_id)
            
            # Get pending guests for this booking
            pending_guests = booking.guests.filter(
                verification_status='pending'
            ).select_related('verified_by').order_by('-created_at')
            
            serializer = AdminGuestListSerializer(pending_guests, many=True, context={'request': request})
            return Response({
                'booking_id': str(booking.id),
                'count': pending_guests.count(),
                'guests': serializer.data
            }, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminVerifyGuestView(APIView):
    """Admin verify a guest - approve them for check-in"""
    permission_classes = [IsAuthenticated]
    serializer_class = AdminVerifyGuestSerializer
    
    @transaction.atomic
    def post(self, request, workspace_id, booking_id, guest_id):
        """
        POST /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/{guest_id}/verify/
        
        Verify a guest and trigger QR code generation/sending
        
        Request body:
        {
            "notes": "Optional notes about the guest"
        }
        """
        # Check permission
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {'error': 'Only admins/managers can verify guests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Verify booking and guest exist
            booking = Booking.objects.get(id=booking_id, workspace_id=workspace_id)
            guest = Guest.objects.select_related('booking').get(
                id=guest_id,
                booking=booking
            )
            
            # Check if already verified or rejected
            if guest.verification_status != 'pending':
                return Response(
                    {
                        'error': f'Guest is already {guest.verification_status}',
                        'current_status': guest.verification_status
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify the guest
            guest.verification_status = 'verified'
            guest.verified_by = request.user
            guest.verified_at = timezone.now()
            guest.status = 'verified'
            guest.save()
            
            # Trigger QR code generation and email sending
            send_guest_qr_code_email.delay(str(guest.id))
            
            # Send notification to booker
            send_notification.delay(
                user_id=str(guest.booking.user.id),
                notification_type='guest_verified',
                channel='email',
                title='Guest Verified',
                message=f'Guest {guest.first_name} {guest.last_name} has been verified. QR code will be sent to their email.',
                data={
                    'guest_id': str(guest.id),
                    'booking_id': str(guest.booking.id),
                    'guest_email': guest.email
                }
            )
            
            serializer = GuestSerializer(guest, context={'request': request})
            return Response({
                'success': True,
                'message': f'Guest {guest.first_name} {guest.last_name} verified successfully',
                'guest': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Guest not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminRejectGuestView(APIView):
    """Admin reject a guest - prevent them from check-in"""
    permission_classes = [IsAuthenticated]
    serializer_class = AdminRejectGuestSerializer
    
    @transaction.atomic
    def post(self, request, workspace_id, booking_id, guest_id):
        """
        POST /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/{guest_id}/reject/
        
        Reject a guest and notify the booker
        
        Request body:
        {
            "reason": "Required reason for rejection"
        }
        """
        # Check permission
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {'error': 'Only admins/managers can reject guests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Verify booking and guest exist
            booking = Booking.objects.get(id=booking_id, workspace_id=workspace_id)
            guest = Guest.objects.select_related('booking').get(
                id=guest_id,
                booking=booking
            )
            
            # Check if already verified or rejected
            if guest.verification_status != 'pending':
                return Response(
                    {
                        'error': f'Guest is already {guest.verification_status}',
                        'current_status': guest.verification_status
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AdminRejectGuestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            reason = serializer.validated_data['reason']
            
            # Reject the guest
            guest.verification_status = 'rejected'
            guest.status = 'rejected'
            guest.rejection_reason = reason
            guest.verified_by = request.user
            guest.verified_at = timezone.now()
            guest.save()
            
            # Send notification to booker
            send_notification.delay(
                user_id=str(guest.booking.user.id),
                notification_type='guest_rejected',
                channel='email',
                title='Guest Not Approved',
                message=f'Guest {guest.first_name} {guest.last_name} could not be approved. Reason: {reason}',
                data={
                    'guest_id': str(guest.id),
                    'booking_id': str(guest.booking.id),
                    'rejection_reason': reason
                }
            )
            
            serializer = GuestSerializer(guest, context={'request': request})
            return Response({
                'success': True,
                'message': f'Guest {guest.first_name} {guest.last_name} rejected',
                'reason': reason,
                'guest': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Guest not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminGuestDetailView(APIView):
    """Get detailed information about a guest"""
    permission_classes = [IsAuthenticated]
    serializer_class = GuestSerializer
    
    def get(self, request, workspace_id, booking_id, guest_id):
        """
        GET /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/{guest_id}/
        
        Get detailed guest information
        """
        # Check permission
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager', 'staff']):
            return Response(
                {'error': 'You do not have access to this workspace'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            booking = Booking.objects.get(id=booking_id, workspace_id=workspace_id)
            guest = Guest.objects.select_related(
                'booking', 'verified_by', 'checked_in_by'
            ).get(
                id=guest_id,
                booking=booking
            )
            
            serializer = GuestSerializer(guest, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Guest.DoesNotExist:
            return Response(
                {'error': 'Guest not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminGuestStatisticsView(APIView):
    """Get guest verification statistics for a booking"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, workspace_id, booking_id):
        """
        GET /api/booking/workspaces/{workspace_id}/admin/bookings/{booking_id}/guests/stats/
        
        Get guest verification statistics
        """
        # Check permission
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager', 'staff']):
            return Response(
                {'error': 'You do not have access to this workspace'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            booking = Booking.objects.get(id=booking_id, workspace_id=workspace_id)
            guests = booking.guests.all()
            
            total = guests.count()
            verified = guests.filter(verification_status='verified').count()
            pending = guests.filter(verification_status='pending').count()
            rejected = guests.filter(verification_status='rejected').count()
            checked_in = guests.filter(status='checked_in').count()
            checked_out = guests.filter(status='checked_out').count()
            
            return Response({
                'booking_id': str(booking.id),
                'statistics': {
                    'total_guests': total,
                    'verified': verified,
                    'pending_verification': pending,
                    'rejected': rejected,
                    'checked_in': checked_in,
                    'checked_out': checked_out,
                    'remaining': total - checked_in - checked_out
                }
            }, status=status.HTTP_200_OK)
            
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

