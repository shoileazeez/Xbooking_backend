"""
Notification ViewSet V1
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.views import CachedModelViewSet
from core.pagination import StandardResultsSetPagination
from core.throttling import UserRateThrottle, UserBurstThrottle
from notifications.models import Notification
from notifications.serializers.v1 import (
    NotificationSerializer,
    NotificationDetailSerializer,
    MarkNotificationReadSerializer,
    BulkMarkReadSerializer
)


class NotificationViewSet(CachedModelViewSet):
    """
    ViewSet for managing user notifications
    
    Endpoints:
    - GET /notifications/ - List all notifications for current user
    - GET /notifications/{id}/ - Retrieve specific notification
    - PATCH /notifications/{id}/mark_read/ - Mark notification as read
    - POST /notifications/mark_all_read/ - Mark all notifications as read
    - POST /notifications/bulk_mark_read/ - Mark multiple notifications as read
    - GET /notifications/unread_count/ - Get count of unread notifications
    """
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    cache_timeout = 60  # 1 minute cache for notifications
    
    def get_queryset(self):
        """Return notifications for current user only"""
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return NotificationDetailSerializer
        return NotificationSerializer
    
    def list(self, request, *args, **kwargs):
        """List notifications with optional filtering"""
        queryset = self.get_queryset()
        
        # Filter by read/unread
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        # Filter by notification type
        notification_type = request.query_params.get('notification_type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Filter by channel
        channel = request.query_params.get('channel')
        if channel:
            queryset = queryset.filter(channel=channel)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def mark_read(self, request, pk=None):
        """
        Mark a single notification as read
        
        PATCH /api/v1/notifications/{id}/mark_read/
        """
        notification = self.get_object()
        serializer = MarkNotificationReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notification.is_read = serializer.validated_data.get('is_read', True)
        if notification.is_read and not notification.read_at:
            notification.read_at = timezone.now()
        
        if serializer.validated_data.get('is_clicked', False):
            notification.is_clicked = True
            if not notification.clicked_at:
                notification.clicked_at = timezone.now()
        
        notification.save()
        
        # Invalidate cache
        self.invalidate_cache(notification)
        
        return Response({
            'message': 'Notification marked as read',
            'notification': NotificationDetailSerializer(notification).data
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all notifications as read for current user
        
        POST /api/v1/notifications/mark_all_read/
        """
        updated_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # Invalidate cache pattern
        self.invalidate_cache_pattern(f'notifications:user:{request.user.id}:*')
        
        return Response({
            'message': f'{updated_count} notifications marked as read',
            'count': updated_count
        })
    
    @action(detail=False, methods=['post'])
    def bulk_mark_read(self, request):
        """
        Mark multiple notifications as read
        
        POST /api/v1/notifications/bulk_mark_read/
        Body: {"notification_ids": ["uuid1", "uuid2", ...]} or {"mark_all": true}
        """
        serializer = BulkMarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if serializer.validated_data.get('mark_all'):
            # Mark all unread notifications
            updated_count = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
        else:
            # Mark specific notifications
            notification_ids = serializer.validated_data.get('notification_ids', [])
            updated_count = Notification.objects.filter(
                user=request.user,
                id__in=notification_ids,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
        
        # Invalidate cache pattern
        self.invalidate_cache_pattern(f'notifications:user:{request.user.id}:*')
        
        return Response({
            'message': f'{updated_count} notifications marked as read',
            'count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications
        
        GET /api/v1/notifications/unread_count/
        """
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return Response({
            'unread_count': count
        })
