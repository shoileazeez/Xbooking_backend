"""
Workspace v1 API URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from workspace.views.v1 import (
    WorkspaceViewSet,
    BranchViewSet,
    SpaceViewSet,
    WorkspaceMemberViewSet,
    AdminUserManagementViewSet,
    PublicWorkspaceViewSet,
    PublicBranchViewSet,
    PublicSpaceViewSet,
    PublicSpaceCalendarViewSet,
    PublicSpaceSlotViewSet,
)

app_name = 'workspace_v1'

# Main router
router = DefaultRouter()
router.register(r'workspaces', WorkspaceViewSet, basename='workspace')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'spaces', SpaceViewSet, basename='space')
router.register(r'members', WorkspaceMemberViewSet, basename='member')

# Nested router for workspace-specific admin endpoints
workspaces_router = routers.NestedDefaultRouter(router, r'workspaces', lookup='workspace')
workspaces_router.register(r'admin/users', AdminUserManagementViewSet, basename='workspace-admin-users')

# Public router
public_router = DefaultRouter()
public_router.register(r'workspaces', PublicWorkspaceViewSet, basename='public-workspace')
public_router.register(r'branches', PublicBranchViewSet, basename='public-branch')
public_router.register(r'spaces', PublicSpaceViewSet, basename='public-space')
public_router.register(r'calendars', PublicSpaceCalendarViewSet, basename='public-calendar')
public_router.register(r'slots', PublicSpaceSlotViewSet, basename='public-slot')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(workspaces_router.urls)),
    path('public/', include(public_router.urls)),
]
