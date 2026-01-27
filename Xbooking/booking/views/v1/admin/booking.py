"""
Admin Booking Views V1 - Booking Management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum
from drf_spectacular.utils import extend_schema

from core.views import CachedModelViewSet
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
from booking.models import Booking, Guest
from booking.serializers.v1 import BookingDetailSerializer, BookingListSerializer
from workspace.models import Workspace
from workspace.permissions import check_workspace_member


class AdminBookingViewSet(CachedModelViewSet):
    """Admin ViewSet for managing bookings in workspaces"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = BookingDetailSerializer
    filterset_fields = ['status', 'booking_type', 'space']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['created_at', 'check_in', 'check_out', 'total_price']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get bookings for workspaces managed by admin"""
        user = self.request.user
        workspace_id = self.kwargs.get('workspace_id')
        
        if workspace_id:
            # Check if user has admin access to this workspace
            workspace = Workspace.objects.filter(id=workspace_id).first()
            if not workspace or not check_workspace_member(user, workspace, ['admin', 'manager']):
                return Booking.objects.none()
            
            return Booking.objects.filter(
                workspace_id=workspace_id
            ).select_related(
                'workspace', 'space', 'user'
            ).prefetch_related('guests')
        
        # Get all bookings from workspaces where user is admin/manager
        return Booking.objects.filter(
            Q(workspace__owner=user) | Q(workspace__members=user)
        ).select_related(
            'workspace', 'space', 'user'
        ).prefetch_related('guests').distinct()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        return BookingDetailSerializer
    
    @extend_schema(
        description="Get booking statistics for workspace",
        responses={200: {
            'type': 'object',
            'properties': {
                'total_bookings': {'type': 'integer'},
                'confirmed': {'type': 'integer'},
                'active': {'type': 'integer'},
                'completed': {'type': 'integer'},
                'cancelled': {'type': 'integer'},
                'total_revenue': {'type': 'string'},
            }
        }}
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request, workspace_id=None):
        """Get booking statistics for workspace"""
        queryset = self.filter_queryset(self.get_queryset())
        
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        
        stats = queryset.aggregate(
            total=Count('id'),
            confirmed=Count('id', filter=Q(status='confirmed')),
            active=Count('id', filter=Q(status='active')),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            total_revenue=Sum('total_price', filter=Q(status__in=['confirmed', 'active', 'completed']))
        )
        
        return SuccessResponse(data={
            'total_bookings': stats['total'],
            'confirmed': stats['confirmed'],
            'active': stats['active'],
            'completed': stats['completed'],
            'cancelled': stats['cancelled'],
            'total_revenue': str(stats['total_revenue'] or 0),
        })
    
    @extend_schema(
        description="Get guest list for a booking"
    )
    @action(detail=True, methods=['get'])
    def guests(self, request, pk=None, workspace_id=None):
        """Get guests for a booking"""
        booking = self.get_object()
        
        from booking.serializers.v1 import GuestSerializer
        guests = booking.guests.all()
        serializer = GuestSerializer(guests, many=True)
        
        return SuccessResponse(data=serializer.data)


__all__ = ['AdminBookingViewSet']
