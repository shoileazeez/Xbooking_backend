"""
Core utilities package for Xbooking
Contains shared utilities used across all modules
"""

from .cache import CacheService, cache_key
from .pagination import StandardResultsSetPagination, LargeResultsSetPagination
from .responses import SuccessResponse, ErrorResponse, PaginatedResponse
from .permissions import IsWorkspaceAdmin, IsWorkspaceManager, IsWorkspaceStaff

# Don't import mixins at top level to avoid Django model registration issues
# Import them directly: from core.mixins import UUIDModelMixin, etc.

__all__ = [
    'CacheService',
    'cache_key',
    'StandardResultsSetPagination',
    'LargeResultsSetPagination',
    'SuccessResponse',
    'ErrorResponse',
    'PaginatedResponse',
    'IsWorkspaceAdmin',
    'IsWorkspaceManager',
    'IsWorkspaceStaff',
]
