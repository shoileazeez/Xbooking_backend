"""
Admin views for managing guest verifications per booking
Allows admins/managers to verify or reject guests before QR code is sent
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from booking.models import Booking, Guest
from booking.guest_serializers import GuestSerializer
from workspace.permissions import check_workspace_member


class AdminGuestDetailView(APIView):
    """Get detailed information about a guest"""
    permission_classes = [IsAuthenticated]
    serializer_class = GuestSerializer
    
    def get(self, request, guest_id):
        """
        GET /api/booking/guests/{guest_id}/
        
        Get detailed guest information
        """
        try:
            guest = Guest.objects.select_related(
                'booking__workspace', 'checked_in_by'
            ).get(id=guest_id)
            
            workspace = guest.booking.workspace
            
            # Check permission
            if not check_workspace_member(request.user, workspace, ['admin', 'manager', 'staff']):
                return Response(
                    {'error': 'You do not have access to this workspace'},
                    status=status.HTTP_403_FORBIDDEN
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
    
    def get(self, request, booking_id):
        """
        GET /api/booking/bookings/{booking_id}/guests/stats/
        
        Get guest verification statistics
        """
        try:
            booking = Booking.objects.get(id=booking_id)
            
            # Check permission
            if not check_workspace_member(request.user, booking.workspace, ['admin', 'manager', 'staff']):
                return Response(
                    {'error': 'You do not have access to this workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            guests = booking.guests.all()
            
            total = guests.count()
            checked_in = guests.filter(status='checked_in').count()
            checked_out = guests.filter(status='checked_out').count()
            
            return Response({
                'booking_id': str(booking.id),
                'statistics': {
                    'total_guests': total,
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

