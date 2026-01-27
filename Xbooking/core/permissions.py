"""
Custom permissions for workspace-based access control
"""

from rest_framework import permissions


class IsWorkspaceAdmin(permissions.BasePermission):
    """
    Permission for workspace admin role
    """
    message = "You must be a workspace administrator to perform this action."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has workspace_admin role in User model
        if hasattr(request.user, 'role') and request.user.role == 'workspace_admin':
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is admin of the workspace
        if hasattr(obj, 'workspace'):
            workspace = obj.workspace
        elif hasattr(obj, 'admin'):
            return obj.admin == request.user
        else:
            workspace = obj
        
        # Check if user is admin
        if hasattr(workspace, 'admin') and workspace.admin == request.user:
            return True
        
        # Check workspace membership with admin role
        if hasattr(workspace, 'members'):
            return workspace.members.filter(
                user=request.user,
                role='admin',
                is_active=True
            ).exists()
        
        return False


class IsWorkspaceManager(permissions.BasePermission):
    """
    Permission for workspace manager role (admin or manager)
    """
    message = "You must be a workspace admin or manager to perform this action."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get workspace from object
        if hasattr(obj, 'workspace'):
            workspace = obj.workspace
        elif hasattr(obj, 'branch'):
            workspace = obj.branch.workspace
        else:
            workspace = obj
        
        # Check if user is workspace admin
        if hasattr(workspace, 'admin') and workspace.admin == request.user:
            return True
        
        # Check workspace membership with admin or manager role
        if hasattr(workspace, 'members'):
            return workspace.members.filter(
                user=request.user,
                role__in=['admin', 'manager'],
                is_active=True
            ).exists()
        
        return False


class IsWorkspaceStaff(permissions.BasePermission):
    """
    Permission for workspace staff (admin, manager, or staff)
    """
    message = "You must be a workspace staff member to perform this action."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get workspace from object
        if hasattr(obj, 'workspace'):
            workspace = obj.workspace
        elif hasattr(obj, 'branch'):
            workspace = obj.branch.workspace
        elif hasattr(obj, 'space'):
            workspace = obj.space.branch.workspace
        else:
            workspace = obj
        
        # Check if user is workspace admin
        if hasattr(workspace, 'admin') and workspace.admin == request.user:
            return True
        
        # Check workspace membership with any staff role
        if hasattr(workspace, 'members'):
            return workspace.members.filter(
                user=request.user,
                role__in=['admin', 'manager', 'staff'],
                is_active=True
            ).exists()
        
        return False


class IsWorkspaceMember(permissions.BasePermission):
    """
    Permission for any workspace member
    """
    message = "You must be a workspace member to perform this action."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get workspace from object
        if hasattr(obj, 'workspace'):
            workspace = obj.workspace
        elif hasattr(obj, 'branch'):
            workspace = obj.branch.workspace
        elif hasattr(obj, 'space'):
            workspace = obj.space.branch.workspace
        else:
            workspace = obj
        
        # Check if user is workspace admin
        if hasattr(workspace, 'admin') and workspace.admin == request.user:
            return True
        
        # Check workspace membership
        if hasattr(workspace, 'members'):
            return workspace.members.filter(
                user=request.user,
                is_active=True
            ).exists()
        
        return False
