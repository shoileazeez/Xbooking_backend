"""
Base view classes with built-in caching and best practices
"""

from rest_framework import viewsets, generics
from rest_framework.response import Response
from core.cache import CacheService
from core.responses import SuccessResponse, ErrorResponse
from core.pagination import StandardResultsSetPagination
import logging

logger = logging.getLogger(__name__)


class CachedModelViewSet(viewsets.ModelViewSet):
    """
    ViewSet with built-in caching for list and retrieve operations
    """
    cache_timeout = CacheService.TIMEOUT_MEDIUM
    pagination_class = StandardResultsSetPagination
    
    def get_cache_key(self, action, **kwargs):
        """Generate cache key for current request"""
        # Handle both queryset attribute and get_queryset() method
        if hasattr(self, 'queryset') and self.queryset is not None:
            model_name = self.queryset.model.__name__.lower()
        else:
            # Get queryset dynamically
            queryset = self.get_queryset()
            model_name = queryset.model.__name__.lower()
        
        params = {
            'action': action,
            'user_id': str(self.request.user.id) if self.request.user.is_authenticated else 'anonymous',
            **kwargs,
            **self.request.query_params.dict()
        }
        return CacheService.generate_key(model_name, **params)
    
    def list(self, request, *args, **kwargs):
        """List with caching"""
        cache_key = self.get_cache_key('list')
        cached_response = CacheService.get(cache_key)
        
        if cached_response is not None:
            queryset = self.get_queryset()
            logger.debug(f"Returning cached list for {queryset.model.__name__}")
            return Response(cached_response)
        
        response = super().list(request, *args, **kwargs)
        
        if response.status_code == 200:
            CacheService.set(cache_key, response.data, self.cache_timeout)
        
        return response
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve with caching"""
        cache_key = self.get_cache_key('retrieve', pk=kwargs.get('pk'))
        cached_response = CacheService.get(cache_key)
        
        if cached_response is not None:
            queryset = self.get_queryset()
            logger.debug(f"Returning cached instance for {queryset.model.__name__}")
            return Response(cached_response)
        
        response = super().retrieve(request, *args, **kwargs)
        
        if response.status_code == 200:
            CacheService.set(cache_key, response.data, self.cache_timeout)
        
        return response
    
    def perform_create(self, serializer):
        """Invalidate cache on create"""
        instance = serializer.save()
        queryset = self.get_queryset()
        model_name = queryset.model.__name__.lower()
        CacheService.invalidate_model(model_name)
        return instance
    
    def perform_update(self, serializer):
        """Invalidate cache on update"""
        instance = serializer.save()
        queryset = self.get_queryset()
        model_name = queryset.model.__name__.lower()
        CacheService.invalidate_model(model_name, str(instance.pk))
        return instance
    
    def perform_destroy(self, instance):
        """Invalidate cache on delete"""
        queryset = self.get_queryset()
        model_name = queryset.model.__name__.lower()
        CacheService.invalidate_model(model_name, str(instance.pk))
        instance.delete()
    
    def invalidate_cache_pattern(self, pattern):
        """Invalidate cache by pattern"""
        # Use cache service to invalidate by pattern
        try:
            CacheService.delete_pattern(pattern)
        except AttributeError:
            # Fallback if delete_pattern not implemented
            logger.warning(f"Cache pattern invalidation not supported: {pattern}")
            pass


class BaseAPIView(generics.GenericAPIView):
    """
    Base API view with standardized responses
    """
    
    def success_response(self, data=None, message="Operation successful", status_code=200):
        """Return standardized success response"""
        return SuccessResponse(data=data, message=message, status_code=status_code)
    
    def error_response(self, message="Operation failed", errors=None, status_code=400):
        """Return standardized error response"""
        return ErrorResponse(message=message, errors=errors, status_code=status_code)
    
    def handle_exception(self, exc):
        """Handle exceptions consistently"""
        logger.error(f"Exception in {self.__class__.__name__}: {str(exc)}")
        return super().handle_exception(exc)
