"""
Push Notification Models
Stores web push notification subscriptions for users
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PushSubscription(models.Model):
    """
    Stores web push notification subscription data for users
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.TextField(unique=True)
    p256dh_key = models.TextField()
    auth_key = models.TextField()
    
    # Browser/device info
    user_agent = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'push_subscriptions'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['endpoint']),
        ]
    
    def __str__(self):
        return f"Push subscription for {self.user.email} ({self.endpoint[:50]}...)"
    
    def to_dict(self):
        """Convert subscription to format needed by pywebpush"""
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh_key,
                "auth": self.auth_key
            }
        }
