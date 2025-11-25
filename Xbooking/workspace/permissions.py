"""
Workspace permissions module for role-based access control
"""
from rest_framework import permissions
from django.shortcuts import get_object_or_404
from workspace.models import Workspace, Branch, WorkspaceUser


class BaseWorkspacePermission(permissions.BasePermission):
    """Base permission class for workspace operations"""
    
    @staticmethod
    def get_user_role_in_workspace(user, workspace):
        """Get the role of a user in a specific workspace"""
        if workspace.admin == user:
            return 'admin'
        
        membership = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=user,
            is_active=True
        ).first()
        
        if membership:
            return membership.role
        
        return None
    
    @staticmethod
    def is_workspace_admin(user, workspace):
        """Check if user is workspace admin"""
        return workspace.admin == user
    
    @staticmethod
    def is_workspace_manager(user, workspace):
        """Check if user is workspace manager or admin"""
        if workspace.admin == user:
            return True
        
        membership = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=user,
            role='manager',
            is_active=True
        ).exists()
        
        return membership
    
    @staticmethod
    def is_workspace_staff(user, workspace):
        """Check if user is workspace staff, manager, or admin"""
        if workspace.admin == user:
            return True
        
        membership = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=user,
            role__in=['staff', 'manager'],
            is_active=True
        ).exists()
        
        return membership
    
    @staticmethod
    def is_workspace_member(user, workspace):
        """Check if user is any member of workspace (including users who book)"""
        if workspace.admin == user:
            return True
        
        membership = WorkspaceUser.objects.filter(
            workspace=workspace,
            user=user,
            is_active=True
        ).exists()
        
        return membership


class IsWorkspaceAdmin(BaseWorkspacePermission):
    """Permission: User must be workspace admin"""
    message = "You must be a workspace admin to perform this action."
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Workspace):
            return self.is_workspace_admin(request.user, obj)
        elif isinstance(obj, Branch):
            return self.is_workspace_admin(request.user, obj.workspace)
        return False


class IsWorkspaceManagerOrAdmin(BaseWorkspacePermission):
    """Permission: User must be workspace manager or admin"""
    message = "You must be a workspace manager or admin to perform this action."
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Workspace):
            return self.is_workspace_manager(request.user, obj)
        elif isinstance(obj, Branch):
            return self.is_workspace_manager(request.user, obj.workspace)
        return False


class IsWorkspaceStaffOrAbove(BaseWorkspacePermission):
    """Permission: User must be workspace staff, manager, or admin"""
    message = "You must be a workspace staff member or above to perform this action."
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Workspace):
            return self.is_workspace_staff(request.user, obj)
        elif isinstance(obj, Branch):
            return self.is_workspace_staff(request.user, obj.workspace)
        return False


class IsWorkspaceMember(BaseWorkspacePermission):
    """Permission: User must be a workspace member"""
    message = "You must be a workspace member to access this resource."
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Workspace):
            return self.is_workspace_member(request.user, obj)
        elif isinstance(obj, Branch):
            return self.is_workspace_member(request.user, obj.workspace)
        return False


class CanCreateWorkspace(permissions.BasePermission):
    """Permission: Authenticated users can create workspaces"""
    message = "You must be authenticated to create a workspace."
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class CanCreateBranch(BaseWorkspacePermission):
    """Permission: Only workspace admin can create branches"""
    message = "Only workspace admin can create branches."
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class CanCreateSpace(BaseWorkspacePermission):
    """Permission: Workspace admin or manager can create spaces"""
    message = "Only workspace admin or manager can create spaces."
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class CanBookSpace(BaseWorkspacePermission):
    """Permission: Workspace members (including users) can book spaces"""
    message = "You must be a workspace member to book a space."
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class CanManageWorkspaceMembers(BaseWorkspacePermission):
    """Permission: Only workspace admin and managers can manage members"""
    message = "Only workspace admin or managers can manage workspace members."
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


# Permission helper functions for use in views

def check_workspace_admin(user, workspace):
    """Check if user is workspace admin"""
    return workspace.admin == user


def check_workspace_manager(user, workspace):
    """Check if user is workspace manager or admin"""
    if workspace.admin == user:
        return True
    return WorkspaceUser.objects.filter(
        workspace=workspace,
        user=user,
        role='manager',
        is_active=True
    ).exists()


def check_workspace_staff(user, workspace):
    """Check if user is workspace staff, manager, or admin"""
    if workspace.admin == user:
        return True
    return WorkspaceUser.objects.filter(
        workspace=workspace,
        user=user,
        role__in=['staff', 'manager'],
        is_active=True
    ).exists()


def check_workspace_member(user, workspace, required_roles=None):
    """
    Check if user is a member of the workspace with specific roles.
    If required_roles is None or empty, checks if user is any member.
    """
    if workspace.admin == user:
        return True
        
    query = WorkspaceUser.objects.filter(
        workspace=workspace,
        user=user,
        is_active=True
    )
    
    if required_roles:
        if isinstance(required_roles, str):
            required_roles = [required_roles]
        query = query.filter(role__in=required_roles)
        
    return query.exists()


def get_user_role(user, workspace):
    """Get the role of a user in a specific workspace"""
    if workspace.admin == user:
        return 'admin'
    
    membership = WorkspaceUser.objects.filter(
        workspace=workspace,
        user=user,
        is_active=True
    ).first()
    
    if membership:
        return membership.role
    
    return None


def check_branch_manager(user, branch):
    """Check if user is branch manager"""
    if branch.workspace.admin == user:
        return True
    
    if branch.manager == user:
        return True
    
    return check_workspace_manager(user, branch.workspace)


def check_branch_access(user, branch):
    """Check if user has any access to branch"""
    return check_workspace_member(user, branch.workspace)


# Role hierarchy mapping
ROLE_HIERARCHY = {
    'admin': ['admin', 'manager', 'staff', 'user'],
    'manager': ['manager', 'staff', 'user'],
    'staff': ['staff', 'user'],
    'user': ['user'],
}


def has_role_or_higher(user_role, required_role):
    """Check if user role is equal to or higher than required role"""
    if not user_role:
        return False
    
    return required_role in ROLE_HIERARCHY.get(user_role, [])
