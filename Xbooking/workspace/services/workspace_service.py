"""
Workspace Service Layer
Handles business logic and event publishing for workspace operations.
"""
from typing import Dict, Any, Optional
from django.db import models
from django.utils import timezone

from core.services import EventBus, Event, EventTypes
from core.cache import CacheService


class WorkspaceService:
    """
    Service class for workspace business logic.
    Publishes events for inter-module communication.
    """
    
    @staticmethod
    def create_workspace(workspace, created_by) -> None:
        """
        Handle workspace creation business logic.
        
        Args:
            workspace: The created workspace instance
            created_by: User who created the workspace
        """
        # Clear user's workspace cache
        CacheService.delete(f"user_workspaces:{created_by.id}")
        
        # Publish workspace created event
        event = Event(
            event_type=EventTypes.WORKSPACE_CREATED,
            data={
                'workspace_id': str(workspace.id),
                'workspace_name': workspace.name,
                'owner_id': str(created_by.id),
                'owner_email': created_by.email,
                'owner_name': created_by.full_name,
                'created_at': timezone.now().isoformat(),
            },
            source_module='workspace'
        )
        EventBus.publish(event)
    
    @staticmethod
    def update_workspace(workspace, updated_by) -> None:
        """
        Handle workspace update business logic.
        
        Args:
            workspace: The updated workspace instance
            updated_by: User who updated the workspace
        """
        # Clear workspace cache
        CacheService.delete(workspace.get_cache_key())
        CacheService.delete(f"user_workspaces:{updated_by.id}")
        
        # Publish workspace updated event
        event = Event(
            event_type=EventTypes.WORKSPACE_UPDATED,
            data={
                'workspace_id': str(workspace.id),
                'workspace_name': workspace.name,
                'updated_by_id': str(updated_by.id),
                'updated_at': timezone.now().isoformat(),
            },
            source_module='workspace'
        )
        EventBus.publish(event)
    
    @staticmethod
    def delete_workspace(workspace, deleted_by) -> None:
        """
        Handle workspace deletion business logic.
        
        Args:
            workspace: The workspace instance being deleted
            deleted_by: User who deleted the workspace
        """
        # Clear all related caches
        CacheService.delete(workspace.get_cache_key())
        CacheService.delete(f"user_workspaces:{deleted_by.id}")
        CacheService.delete_pattern(f"workspace:{workspace.id}:*")
        
        # Publish workspace deleted event
        event = Event(
            event_type=EventTypes.WORKSPACE_DELETED,
            data={
                'workspace_id': str(workspace.id),
                'workspace_name': workspace.name,
                'deleted_by_id': str(deleted_by.id),
                'deleted_at': timezone.now().isoformat(),
            },
            source_module='workspace'
        )
        EventBus.publish(event)
    
    @staticmethod
    def add_member(workspace, user, role='staff', added_by=None) -> None:
        """
        Handle adding member to workspace.
        
        Args:
            workspace: The workspace instance
            user: User being added
            role: Role of the user
            added_by: User who added the member
        """
        # Clear caches
        CacheService.delete(f"workspace_members:{workspace.id}")
        CacheService.delete(f"user_workspaces:{user.id}")
        
        # Publish member added event
        event = Event(
            event_type=EventTypes.WORKSPACE_MEMBER_ADDED,
            data={
                'workspace_id': str(workspace.id),
                'workspace_name': workspace.name,
                'user_id': str(user.id),
                'user_email': user.email,
                'user_name': user.full_name,
                'role': role,
                'added_by_id': str(added_by.id) if added_by else None,
                'added_by_name': added_by.full_name if added_by else None,
                'added_at': timezone.now().isoformat(),
            },
            source_module='workspace'
        )
        EventBus.publish(event)
    
    @staticmethod
    def remove_member(workspace, user, removed_by=None) -> None:
        """
        Handle removing member from workspace.
        
        Args:
            workspace: The workspace instance
            user: User being removed
            removed_by: User who removed the member
        """
        # Clear caches
        CacheService.delete(f"workspace_members:{workspace.id}")
        CacheService.delete(f"user_workspaces:{user.id}")
        
        # Publish member removed event
        event = Event(
            event_type=EventTypes.WORKSPACE_MEMBER_REMOVED,
            data={
                'workspace_id': str(workspace.id),
                'user_id': str(user.id),
                'removed_by_id': str(removed_by.id) if removed_by else None,
                'removed_at': timezone.now().isoformat(),
            },
            source_module='workspace'
        )
        EventBus.publish(event)
    
    @staticmethod
    def get_workspace_statistics(workspace) -> Dict[str, Any]:
        """
        Get workspace statistics with caching.
        Only includes workspace-owned data, no cross-module queries.
        
        Args:
            workspace: The workspace instance
            
        Returns:
            Dictionary containing workspace statistics
        """
        cache_key = f"workspace_stats:{workspace.id}"
        cached_stats = CacheService.get(cache_key)
        
        if cached_stats is not None:
            return cached_stats
        
        from workspace.models import Branch, Space, WorkspaceUser
        
        stats = {
            'total_branches': Branch.objects.filter(workspace=workspace, is_active=True).count(),
            'total_spaces': Space.objects.filter(branch__workspace=workspace, is_available=True).count(),
            'total_members': WorkspaceUser.objects.filter(workspace=workspace, is_active=True).count(),
        }
        
        # Cache for 5 minutes
        CacheService.set(cache_key, stats, timeout=300)
        
        return stats


class BranchService:
    """Service class for branch business logic"""
    
    @staticmethod
    def create_branch(branch, created_by) -> None:
        """Handle branch creation"""
        # Clear workspace cache
        CacheService.delete(f"workspace_branches:{branch.workspace.id}")
        
        # Publish event
        event = Event(
            event_type=EventTypes.BRANCH_CREATED,
            data={
                'branch_id': str(branch.id),
                'workspace_id': str(branch.workspace.id),
                'branch_name': branch.name,
                'created_by_id': str(created_by.id),
            },
            source_module='workspace'
        )
        EventBus.publish(event)
    
    @staticmethod
    def update_branch(branch, updated_by) -> None:
        """Handle branch update"""
        CacheService.delete(branch.get_cache_key())
        CacheService.delete(f"workspace_branches:{branch.workspace.id}")
        
        event = Event(
            event_type=EventTypes.BRANCH_UPDATED,
            data={
                'branch_id': str(branch.id),
                'workspace_id': str(branch.workspace.id),
                'updated_by_id': str(updated_by.id),
            },
            source_module='workspace'
        )
        EventBus.publish(event)


class SpaceService:
    """Service class for space business logic"""
    
    @staticmethod
    def create_space(space, created_by) -> None:
        """Handle space creation"""
        CacheService.delete(f"branch_spaces:{space.branch.id}")
        
        event = Event(
            event_type=EventTypes.SPACE_CREATED,
            data={
                'space_id': str(space.id),
                'branch_id': str(space.branch.id),
                'space_name': space.name,
                'space_type': space.space_type,
                'created_by_id': str(created_by.id),
            },
            source_module='workspace'
        )
        EventBus.publish(event)
    
    @staticmethod
    def update_space(space, updated_by) -> None:
        """Handle space update"""
        CacheService.delete(space.get_cache_key())
        CacheService.delete(f"branch_spaces:{space.branch.id}")
        
        event = Event(
            event_type=EventTypes.SPACE_UPDATED,
            data={
                'space_id': str(space.id),
                'updated_by_id': str(updated_by.id),
            },
            source_module='workspace'
        )
        EventBus.publish(event)
