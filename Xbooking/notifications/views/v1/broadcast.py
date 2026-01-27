"""
Broadcast Notification ViewSet V1
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import CachedModelViewSet
from core.pagination import StandardResultsSetPagination
from core.throttling import UserRateThrottle
from core.permissions import IsWorkspaceAdmin
from notifications.models import BroadcastNotification
from notifications.serializers.v1 import (
    BroadcastNotificationSerializer,
    CreateBroadcastNotificationSerializer
)
from notifications.tasks import send_broadcast_notification


class BroadcastNotificationViewSet(CachedModelViewSet):
    """
    ViewSet for managing broadcast notifications (workspace admins only)
    
    Endpoints:
    - GET /broadcasts/ - List all broadcasts for workspace
    - POST /broadcasts/ - Create new broadcast
    - GET /broadcasts/{id}/ - Retrieve specific broadcast
    - POST /broadcasts/{id}/send/ - Send broadcast immediately
    """
    
    serializer_class = BroadcastNotificationSerializer
    permission_classes = [IsWorkspaceAdmin]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [UserRateThrottle]
    cache_timeout = 120  # 2 minutes cache
    
    def get_queryset(self):
        """Return broadcasts for workspaces where user is admin"""
        from workspace.models import WorkspaceUser
        
        # Get workspaces where user is admin
        admin_workspace_ids = WorkspaceUser.objects.filter(
            user=self.request.user,
            role__in=['admin', 'owner']
        ).values_list('workspace_id', flat=True)
        
        return BroadcastNotification.objects.filter(
            workspace_id__in=admin_workspace_ids
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        """Use create serializer for POST"""
        if self.action == 'create':
            return CreateBroadcastNotificationSerializer
        return BroadcastNotificationSerializer
    
    def create(self, request, *args, **kwargs):
        """Create new broadcast notification"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        broadcast = serializer.save(created_by=request.user)
        
        # If not scheduled, send immediately
        if not broadcast.scheduled_at:
            send_broadcast_notification.delay(str(broadcast.id))
            broadcast.status = 'sending'
            broadcast.save()
        
        return Response({
            'message': 'Broadcast created successfully',
            'broadcast': BroadcastNotificationSerializer(broadcast).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Send broadcast notification immediately
        
        POST /api/v1/notifications/broadcasts/{id}/send/
        """
        broadcast = self.get_object()
        
        if broadcast.status != 'draft':
            return Response({
                'error': 'Broadcast has already been sent or is being sent'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Queue broadcast for sending
        send_broadcast_notification.delay(str(broadcast.id))
        
        broadcast.status = 'sending'
        broadcast.save()
        
        # Invalidate cache
        self.invalidate_cache(broadcast)
        
        return Response({
            'message': 'Broadcast queued for sending',
            'broadcast': BroadcastNotificationSerializer(broadcast).data
        })
