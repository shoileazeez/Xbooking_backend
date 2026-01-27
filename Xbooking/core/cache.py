"""
Redis caching utilities for Xbooking
Provides centralized caching service with consistent key naming
"""

import json
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """
    Centralized caching service for consistent cache management
    """
    
    # Default cache timeouts (in seconds)
    TIMEOUT_SHORT = 60 * 5  # 5 minutes
    TIMEOUT_MEDIUM = 60 * 30  # 30 minutes
    TIMEOUT_LONG = 60 * 60 * 2  # 2 hours
    TIMEOUT_VERY_LONG = 60 * 60 * 24  # 24 hours
    
    @staticmethod
    def generate_key(prefix: str, *args, **kwargs) -> str:
        """
        Generate a cache key from prefix and parameters
        
        Args:
            prefix: Key prefix (e.g., 'workspace', 'booking')
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            Generated cache key
        """
        # Combine all parameters
        params = list(args) + sorted(kwargs.items())
        params_str = json.dumps(params, sort_keys=True, default=str)
        
        # Create hash for long parameter strings
        if len(params_str) > 100:
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            return f"{prefix}:{params_hash}"
        
        return f"{prefix}:{params_str}"
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Get value from cache
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            value = cache.get(key, default)
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache GET error for {key}: {str(e)}")
            return default
    
    @staticmethod
    def set(key: str, value: Any, timeout: int = TIMEOUT_MEDIUM) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache.set(key, value, timeout)
            logger.debug(f"Cache SET: {key} (timeout={timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Cache SET error for {key}: {str(e)}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error for {key}: {str(e)}")
            return False
    
    @staticmethod
    def delete_pattern(pattern: str) -> bool:
        """
        Delete all keys matching pattern
        Requires Redis backend
        
        Args:
            pattern: Key pattern (e.g., 'workspace:*')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache.delete_pattern(pattern)
            logger.debug(f"Cache DELETE PATTERN: {pattern}")
            return True
        except Exception as e:
            logger.error(f"Cache DELETE PATTERN error for {pattern}: {str(e)}")
            return False
    
    @staticmethod
    def get_or_set(key: str, default_func: Callable, timeout: int = TIMEOUT_MEDIUM) -> Any:
        """
        Get from cache or set if not exists
        
        Args:
            key: Cache key
            default_func: Function to call if cache miss
            timeout: Cache timeout in seconds
            
        Returns:
            Cached or newly set value
        """
        value = CacheService.get(key)
        
        if value is None:
            value = default_func()
            CacheService.set(key, value, timeout)
        
        return value
    
    @staticmethod
    def invalidate_model(model_name: str, instance_id: Optional[str] = None):
        """
        Invalidate cache for a model
        
        Args:
            model_name: Name of the model (e.g., 'workspace')
            instance_id: Optional specific instance ID
        """
        if instance_id:
            pattern = f"{model_name}:{instance_id}:*"
        else:
            pattern = f"{model_name}:*"
        
        CacheService.delete_pattern(pattern)
        logger.info(f"Invalidated cache for {model_name}" + (f":{instance_id}" if instance_id else ""))


def cache_key(prefix: str, timeout: int = CacheService.TIMEOUT_MEDIUM):
    """
    Decorator to cache function results
    
    Args:
        prefix: Cache key prefix
        timeout: Cache timeout in seconds
        
    Usage:
        @cache_key('user_profile', timeout=300)
        def get_user_profile(user_id):
            return User.objects.get(id=user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            key = CacheService.generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = CacheService.get(key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            CacheService.set(key, result, timeout)
            
            return result
        
        return wrapper
    return decorator


def cache_model_instance(timeout: int = CacheService.TIMEOUT_MEDIUM):
    """
    Decorator to cache model instance methods
    
    Usage:
        class MyModel:
            @cache_model_instance(timeout=300)
            def get_related_data(self):
                return expensive_query()
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            model_name = self.__class__.__name__.lower()
            instance_id = str(self.pk)
            func_name = func.__name__
            
            key = CacheService.generate_key(
                f"{model_name}:{instance_id}:{func_name}",
                *args,
                **kwargs
            )
            
            return CacheService.get_or_set(
                key,
                lambda: func(self, *args, **kwargs),
                timeout
            )
        
        return wrapper
    return decorator
