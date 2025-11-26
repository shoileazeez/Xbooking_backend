"""
Notification views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from notifications.models import Notification, NotificationPreference, BroadcastNotification
from notifications.serializers import (
    NotificationSerializer, NotificationPreferenceSerializer, 
    BroadcastNotificationSerializer, CreateBroadcastNotificationSerializer
)
from workspace.permissions import check_workspace_member
from drf_spectacular.utils import extend_schema


class GetUserNotificationsView(APIView):
    """Get user notifications"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get user notifications",
        description="Get all notifications for the current user with optional filtering",
        tags=["Notifications"],
        parameters=[
            {'name': 'unread_only', 'in': 'query', 'schema': {'type': 'boolean'}, 'description': 'Filter only unread notifications'},
            {'name': 'notification_type', 'in': 'query', 'schema': {'type': 'string'}, 'description': 'Filter by notification type'},
            {'name': 'channel', 'in': 'query', 'schema': {'type': 'string'}, 'description': 'Filter by channel'},
        ],
        responses={200: NotificationSerializer(many=True)}
    )
    @method_decorator(cache_page(60 * 2))  # Cache for 2 minutes
    def get(self, request):
        """Get notifications"""
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        notification_type = request.query_params.get('notification_type')
        channel = request.query_params.get('channel')
        
        # Build query
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        
        if unread_only:
            notifications = notifications.filter(is_read=False)
        
        if notification_type:
            notifications = notifications.filter(notification_type=notification_type)
        
        if channel:
            notifications = notifications.filter(channel=channel)
        
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginated_notifications = paginator.paginate_queryset(notifications, request)
        
        serializer = NotificationSerializer(paginated_notifications, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class MarkNotificationAsReadView(APIView):
    """Mark a single notification as read"""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    
    @extend_schema(
        summary="Mark notification as read",
        description="Mark a single notification as read",
        tags=["Notifications"],
        responses={200: NotificationSerializer}
    )
    def post(self, request, notification_id):
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.mark_as_read()
            
            serializer = NotificationSerializer(notification, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class MarkAllNotificationsAsReadView(APIView):
    """Mark all user notifications as read"""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    
    @extend_schema(
        summary="Mark all notifications as read",
        description="Mark all unread notifications as read",
        tags=["Notifications"],
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}, "updated_count": {"type": "integer"}}}}
    )
    def post(self, request):
        """Mark all as read"""
        unread_notifications = Notification.objects.filter(user=request.user, is_read=False)
        count = unread_notifications.count()
        
        for notification in unread_notifications:
            notification.mark_as_read()
        
        return Response(
            {
                "message": f"{count} notification(s) marked as read",
                "updated_count": count
            },
            status=status.HTTP_200_OK
        )


class GetNotificationPreferencesView(APIView):
    """Get user notification preferences"""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer
    
    @extend_schema(
        summary="Get notification preferences",
        description="Get current user notification preferences",
        tags=["Notification Preferences"],
        responses={200: NotificationPreferenceSerializer}
    )
    def get(self, request):
        """Get preferences"""
        try:
            preferences = NotificationPreference.objects.get(user=request.user)
        except NotificationPreference.DoesNotExist:
            # Create default preferences if not exist
            preferences = NotificationPreference.objects.create(user=request.user)
        
        serializer = NotificationPreferenceSerializer(preferences, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateNotificationPreferencesView(APIView):
    """Update user notification preferences"""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer
    
    @extend_schema(
        summary="Update notification preferences",
        description="Update current user notification preferences",
        tags=["Notification Preferences"],
        request=NotificationPreferenceSerializer,
        responses={200: NotificationPreferenceSerializer}
    )
    def patch(self, request):
        """Update preferences"""
        try:
            preferences = NotificationPreference.objects.get(user=request.user)
        except NotificationPreference.DoesNotExist:
            preferences = NotificationPreference.objects.create(user=request.user)
        
        serializer = NotificationPreferenceSerializer(preferences, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminSendBroadcastNotificationView(APIView):
    """Send broadcast notification to workspace users"""
    permission_classes = [IsAuthenticated]
    serializer_class = CreateBroadcastNotificationSerializer
    
    @extend_schema(
        summary="Send broadcast notification",
        description="Admin/Manager sends broadcast notification to workspace users",
        tags=["Admin Notifications"],
        request=CreateBroadcastNotificationSerializer,
        responses={
            201: BroadcastNotificationSerializer,
            403: {"type": "object", "properties": {"detail": {"type": "string"}}},
            400: {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    )
    def post(self, request, workspace_id):
        """Send broadcast notification"""
        # Check permissions
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager']):
            return Response(
                {"detail": "You don't have permission to send notifications in this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from workspace.models import Workspace
            workspace = Workspace.objects.get(id=workspace_id)
            
            serializer = CreateBroadcastNotificationSerializer(data=request.data)
            if serializer.is_valid():
                broadcast = serializer.save(
                    workspace=workspace,
                    created_by=request.user,
                    status='sent',
                    sent_at=timezone.now()
                )
                
                # Send notification asynchronously
                from notifications.tasks import send_broadcast_notification
                send_broadcast_notification.delay(str(broadcast.id))
                
                response_serializer = BroadcastNotificationSerializer(broadcast, context={'request': request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminListBroadcastNotificationsView(APIView):
    """List broadcast notifications for workspace"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List broadcast notifications",
        description="Get all broadcast notifications for a workspace",
        tags=["Admin Notifications"],
        responses={200: BroadcastNotificationSerializer(many=True)}
    )
    def get(self, request, workspace_id):
        """Get broadcast notifications"""
        # Check permissions
        if not check_workspace_member(request.user, workspace_id, ['admin', 'manager', 'staff']):
            return Response(
                {"detail": "You don't have permission to access this workspace"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            broadcasts = BroadcastNotification.objects.filter(workspace_id=workspace_id).order_by('-created_at')
            serializer = BroadcastNotificationSerializer(broadcasts, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
