from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.hashers import make_password, check_password
import uuid
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.mixins import UUIDModelMixin, TimestampedModelMixin, CachedModelMixin


class UserRole(models.TextChoices):
    """User role choices"""
    USER = 'user', _('User')
    WORKSPACE_ADMIN = 'workspace_admin', _('Workspace Admin')


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        # Default role is USER
        extra_fields.setdefault('role', UserRole.USER)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.WORKSPACE_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(UUIDModelMixin, TimestampedModelMixin, CachedModelMixin, AbstractBaseUser, PermissionsMixin):
    """User model with role-based access control"""
    full_name = models.CharField(max_length=200, null=False, blank=False)
    email = models.EmailField(unique=True, blank=False)
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    
    # Role and business email fields
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
        help_text='User role in the system'
    )
    is_business_email = models.BooleanField(
        default=False,
        help_text='Whether email is a business email (not free provider)'
    )
    business_domain = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Business email domain'
    )
    
    # Onboarding fields
    onboarding_completed = models.BooleanField(
        default=False,
        help_text='Whether user has completed onboarding'
    )
    
    # OAuth fields
    google_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    force_password_change = models.BooleanField(
        default=False,
        help_text="Force user to change password on next login"
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        db_table = 'user'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.full_name or self.email
    
    def get_cache_key(self):
        """Generate cache key for this user"""
        return f"user:{self.id}"
    
    def is_workspace_admin(self):
        """Check if user is a workspace admin"""
        return self.role == UserRole.WORKSPACE_ADMIN
    
    def is_regular_user(self):
        """Check if user is a regular user"""
        return self.role == UserRole.USER


class VerificationCode(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """Email verification codes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'user_verification_code'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Verification code for {self.user.email}"
    
    def is_valid(self):
        """Check if code is still valid"""
        return not self.is_used and timezone.now() < self.expires_at


class UserPreference(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """
    Model to store user preferences for bookings and space recommendations
    """
    
    PREFERRED_BOOKING_TYPES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
    ]
    
    PREFERRED_SPACE_TYPES = [
        ('meeting_room', 'Meeting Room'),
        ('office', 'Office'),
        ('coworking', 'Coworking Space'),
        ('event_space', 'Event Space'),
        ('desk', 'Dedicated Desk'),
        ('lounge', 'Lounge'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    
    # Booking Preferences
    preferred_booking_type = models.CharField(
        max_length=20,
        choices=PREFERRED_BOOKING_TYPES,
        default='hourly',
        help_text='Preferred booking duration type'
    )
    
    preferred_space_types = models.JSONField(
        default=list,
        blank=True,
        help_text='List of preferred space types'
    )
    
    preferred_capacity_min = models.IntegerField(
        default=1,
        help_text='Minimum preferred space capacity'
    )
    
    preferred_capacity_max = models.IntegerField(
        default=10,
        help_text='Maximum preferred space capacity'
    )
    
    # Location Preferences
    preferred_cities = models.JSONField(
        default=list,
        blank=True,
        help_text='List of preferred cities'
    )
    
    max_distance_km = models.FloatField(
        default=10.0,
        null=True,
        blank=True,
        help_text='Maximum distance from user location in kilometers'
    )
    
    # Amenity Preferences
    preferred_amenities = models.JSONField(
        default=list,
        blank=True,
        help_text='List of must-have amenities'
    )
    
    # Budget Preferences
    budget_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Minimum budget per booking'
    )
    
    budget_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Maximum budget per booking'
    )
    
    # Time Preferences
    preferred_days_of_week = models.JSONField(
        default=list,
        blank=True,
        help_text='Preferred days of week (0=Sunday, 6=Saturday)'
    )
    
    preferred_start_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Preferred booking start time'
    )
    
    preferred_end_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Preferred booking end time'
    )
    
    # Notification Preferences
    notify_recommendations = models.BooleanField(
        default=True,
        help_text='Receive space recommendations'
    )
    
    notify_price_drops = models.BooleanField(
        default=True,
        help_text='Notify about price drops'
    )
    
    notify_new_spaces = models.BooleanField(
        default=True,
        help_text='Notify about new spaces'
    )
    
    # Advanced Preferences
    auto_suggest_similar = models.BooleanField(
        default=True,
        help_text='Auto-suggest similar spaces'
    )
    
    save_search_history = models.BooleanField(
        default=True,
        help_text='Save search history'
    )
    
    class Meta:
        db_table = 'user_preference'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Preferences for {self.user.email}"
