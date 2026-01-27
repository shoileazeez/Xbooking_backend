"""
Workspace-specific permissions and helper functions
Extends core permissions for workspace role checking
"""
from workspace.models import Workspace, Branch, WorkspaceUser


# Helper functions for workspace role checking

def get_user_role(user, workspace):
    """Get the role of a user in a specific workspace"""
    if workspace.admin == user:
        return 'admin'
    
    membership = WorkspaceUser.objects.filter(
        workspace=workspace,
        user=user,
        is_active=True
    ).first()
    
    return membership.role if membership else None


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


# Role hierarchy for checking role levels
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

