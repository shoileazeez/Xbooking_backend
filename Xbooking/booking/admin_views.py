"""
Admin views for managing bookings in workspace
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from booking.models import Booking, BookingReview
from booking.serializers import BookingListSerializer, BookingDetailSerializer, BookingReviewSerializer
from booking.admin_serializers import AdminUpdateBookingStatusSerializer, AdminBookingFilterSerializer
from workspace.permissions import check_workspace_member
from drf_spectacular.utils import extend_schema
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import uuid


class AdminListBookingsView(APIView):
    """List all bookings for a workspace - Admin/Manager only"""
    permission_classes = [IsAuthenticated]
    serializer_class = BookingListSerializer
    
    @extend_schema(
        summary="List all workspace bookings",
        description="Get all bookings in a workspace (Admin/Manager only)",
        tags=["Admin Bookings"],
        responses={
            200: BookingListSerializer(many=True),
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id):
        """Get all bookings for workspace"""
        # Check if user is workspace admin or manager
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            bookings = Booking.objects.filter(workspace_id=workspace_id).select_related(
                'space', 'user', 'space__branch'
            ).order_by('-created_at')
            serializer = BookingListSerializer(bookings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminBookingDetailView(APIView):
    """Get detailed booking information - Admin/Manager only"""
    permission_classes = [IsAuthenticated]
    serializer_class = BookingDetailSerializer
    
    @extend_schema(
        summary="Get booking details",
        description="Get detailed information about a specific booking",
        tags=["Admin Bookings"],
        responses={
            200: BookingDetailSerializer,
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id, booking_id):
        """Get booking details"""
        # Check if user is workspace admin or manager
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            booking = Booking.objects.get(id=booking_id, workspace_id=workspace_id)
            serializer = BookingDetailSerializer(booking)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminUpdateBookingStatusView(APIView):
    """Update booking status - Admin/Manager only"""
    permission_classes = [IsAuthenticated]
    serializer_class = AdminUpdateBookingStatusSerializer
    
    @extend_schema(
        summary="Update booking status",
        description="Update booking status (confirm, complete, cancel)",
        tags=["Admin Bookings"],
        request=AdminUpdateBookingStatusSerializer,
        responses={
            200: BookingDetailSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def patch(self, request, workspace_id, booking_id):
        """Update booking status"""
        # Check if user is workspace admin or manager
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            booking = Booking.objects.get(id=booking_id, workspace_id=workspace_id)
            new_status = request.data.get('status')
            
            if not new_status:
                return Response(
                    {"detail": "Status is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            valid_statuses = ['pending', 'confirmed', 'in_progress', 'completed', 'cancelled']
            if new_status not in valid_statuses:
                return Response(
                    {"detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            booking.status = new_status
            booking.save()
            
            serializer = BookingDetailSerializer(booking)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminBookingsByStatusView(APIView):
    """Filter bookings by status - Admin/Manager only"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List bookings by status",
        description="Get all bookings filtered by status",
        tags=["Admin Bookings"],
        parameters=[{
            "name": "status",
            "in": "query",
            "type": "string",
            "enum": ["pending", "confirmed", "in_progress", "completed", "cancelled"],
            "required": True
        }],
        responses={
            200: BookingListSerializer(many=True),
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id):
        """Get bookings by status"""
        # Check if user is workspace admin or manager
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        status_filter = request.query_params.get('status')
        
        if not status_filter:
            return Response(
                {"detail": "Status query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_statuses = ['pending', 'confirmed', 'in_progress', 'completed', 'cancelled']
        if status_filter not in valid_statuses:
            return Response(
                {"detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            bookings = Booking.objects.filter(
                workspace_id=workspace_id,
                status=status_filter
            ).select_related('space', 'user', 'space__branch').order_by('-created_at')
            
            serializer = BookingListSerializer(bookings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminBookingsBySpaceView(APIView):
    """Get all bookings for a specific space - Admin/Manager only"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List bookings for a space",
        description="Get all bookings for a specific space in workspace",
        tags=["Admin Bookings"],
        responses={
            200: BookingListSerializer(many=True),
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id, space_id):
        """Get bookings for a space"""
        # Check if user is workspace admin or manager
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            bookings = Booking.objects.filter(
                workspace_id=workspace_id,
                space_id=space_id
            ).select_related('space', 'user', 'space__branch').order_by('-created_at')
            
            serializer = BookingListSerializer(bookings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminBookingReviewsView(APIView):
    """Get reviews for a booking - Admin/Manager only"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get booking reviews",
        description="Get all reviews for a completed booking",
        tags=["Admin Bookings"],
        responses={
            200: BookingReviewSerializer(many=True),
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id, booking_id):
        """Get reviews for a booking"""
        # Check if user is workspace admin or manager
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            booking = Booking.objects.get(id=booking_id, workspace_id=workspace_id)
            reviews = BookingReview.objects.filter(booking=booking)
            serializer = BookingReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminBookingStatisticsView(APIView):
    """Get booking statistics for workspace - Admin/Manager only"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get booking statistics",
        description="Get booking statistics (total, by status, revenue, etc.)",
        tags=["Admin Bookings"],
        responses={
            200: {"type": "object", "properties": {
                "total_bookings": {"type": "integer"},
                "pending": {"type": "integer"},
                "confirmed": {"type": "integer"},
                "in_progress": {"type": "integer"},
                "completed": {"type": "integer"},
                "cancelled": {"type": "integer"},
                "total_revenue": {"type": "string"},
                "average_booking_value": {"type": "string"}
            }},
            403: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def get(self, request, workspace_id):
        """Get booking statistics"""
        # Check if user is workspace admin or manager
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            bookings = Booking.objects.filter(workspace_id=workspace_id)
            
            total_revenue = sum(b.total_price for b in bookings if b.status == 'completed')
            total_bookings = bookings.count()
            
            stats = {
                "total_bookings": total_bookings,
                "pending": bookings.filter(status='pending').count(),
                "confirmed": bookings.filter(status='confirmed').count(),
                "in_progress": bookings.filter(status='in_progress').count(),
                "completed": bookings.filter(status='completed').count(),
                "cancelled": bookings.filter(status='cancelled').count(),
                "total_revenue": str(total_revenue),
                "average_booking_value": str(total_revenue / total_bookings) if total_bookings > 0 else "0"
            }
            
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
