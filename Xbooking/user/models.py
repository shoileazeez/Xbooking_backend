from django.db import models
from django.contrib.auth.hashers import make_password, check_password
import uuid
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(models.Model):
    id = models.UUIDField(primary_key = True, editable=False, default=uuid.uuid4)
    full_name = models.CharField(max_length = 200, null=False, blank = False)
    email = models.EmailField(unique = True, blank=False)
    password = models.CharField(blank=True, max_length=255)
    avatar_url = models.URLField(blank=True, null=True)
    google_id = models.CharField(max_length=255, blank=True, null=True)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    last_login = models.DateTimeField(_("last_login"), default=timezone.now)
    is_active = models.BooleanField(default = True)
    force_password_change = models.BooleanField(default=False, help_text="Force user to change password on next login")
    
    # Required fields for custom user model
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    def __str__(self):
        return self.full_name or self.email

    def set_password(self, raw_password):
        if raw_password:
            self.password = make_password(raw_password)
 
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    @property
    def is_anonymous(self):
        """Always return False for logged-in users"""
        return False
    
    @property
    def is_authenticated(self):
        """Return True if user is active"""
        return self.is_active
    
    @property
    def is_staff(self):
        """Return False - we use is_active for admin detection"""
        return False
    
    @property
    def is_superuser(self):
        """Return False - we use is_active for admin detection"""
        return False


class VerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    code = models.CharField(max_length = 6)
    created_at = models.DateTimeField(_("created_at"), default = timezone.now)
    is_used = models.BooleanField(default = False)
    
    def __str__(self):
        return f"Verification code for {self.user.email}"
    
    class Meta:
        ordering = ['-created_at']