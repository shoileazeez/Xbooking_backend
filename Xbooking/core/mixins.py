"""
Model mixins for common functionality
"""

import uuid
from django.db import models
from django.utils import timezone
from core.cache import CacheService


class UUIDModelMixin(models.Model):
    """
    Mixin to add UUID primary key
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True


class TimestampedModelMixin(models.Model):
    """
    Mixin to add created_at and updated_at timestamps
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class SoftDeleteModelMixin(models.Model):
    """
    Mixin for soft delete functionality
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    def delete(self, using=None, keep_parents=False):
        """Soft delete"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def hard_delete(self):
        """Permanent delete"""
        super().delete()
    
    def restore(self):
        """Restore soft deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()
    
    class Meta:
        abstract = True


class CachedModelMixin:
    """
    Mixin to add caching capabilities to models
    """
    
    @classmethod
    def get_cache_key(cls, instance_id):
        """Generate cache key for model instance"""
        return f"{cls.__name__.lower()}:{instance_id}"
    
    def cache_instance(self, timeout=CacheService.TIMEOUT_MEDIUM):
        """Cache this model instance"""
        # Handle both instance method and class method get_cache_key
        if hasattr(self, 'get_cache_key') and callable(self.get_cache_key):
            import inspect
            sig = inspect.signature(self.get_cache_key)
            if len(sig.parameters) == 0:
                key = self.get_cache_key()
            else:
                key = self.__class__.get_cache_key(self.pk)
        else:
            key = self.__class__.get_cache_key(self.pk)
        CacheService.set(key, self, timeout)
    
    @classmethod
    def get_from_cache(cls, instance_id):
        """Get model instance from cache"""
        key = cls.get_cache_key(instance_id)
        return CacheService.get(key)
    
    @classmethod
    def get_or_cache(cls, instance_id, timeout=CacheService.TIMEOUT_MEDIUM):
        """Get from cache or database and cache"""
        cached = cls.get_from_cache(instance_id)
        if cached:
            return cached
        
        try:
            instance = cls.objects.get(pk=instance_id)
            instance.cache_instance(timeout)
            return instance
        except cls.DoesNotExist:
            return None
    
    def invalidate_cache(self):
        """Invalidate cache for this instance"""
        if hasattr(self, 'get_cache_key') and callable(self.get_cache_key):
            # Check if it's an instance method (takes no args) or class method
            import inspect
            sig = inspect.signature(self.get_cache_key)
            if len(sig.parameters) == 0:
                # Instance method like User.get_cache_key(self)
                key = self.get_cache_key()
            else:
                # Class method like CachedModelMixin.get_cache_key(cls, instance_id)
                key = self.__class__.get_cache_key(self.pk)
        else:
            key = self.__class__.get_cache_key(self.pk)
        
        CacheService.delete(key)
        
        # Also invalidate any related patterns
        model_name = self.__class__.__name__.lower()
        CacheService.invalidate_model(model_name, str(self.pk))
    
    def save(self, *args, **kwargs):
        """Override save to invalidate cache"""
        super().save(*args, **kwargs)
        self.invalidate_cache()
    
    def delete(self, *args, **kwargs):
        """Override delete to invalidate cache"""
        self.invalidate_cache()
        super().delete(*args, **kwargs)


class ActiveModelMixin(models.Model):
    """
    Mixin for active/inactive status
    """
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        abstract = True
