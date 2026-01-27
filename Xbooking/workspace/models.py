from django.db import models
from django.core.validators import MinValueValidator, URLValidator
from decimal import Decimal
from user.models import User
import uuid
from core.mixins import UUIDModelMixin, TimestampedModelMixin, CachedModelMixin, ActiveModelMixin


class Workspace(UUIDModelMixin, TimestampedModelMixin, CachedModelMixin, ActiveModelMixin, models.Model):
    """Model for workspace/organization"""
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_workspaces')
    logo_url = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True, validators=[URLValidator()])
    email = models.EmailField(unique=True)
    social_media_links = models.JSONField(default=dict, blank=True, help_text='Store social media links as key-value pairs')
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'workspace'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    def get_cache_key(self):
        """Generate cache key for this workspace"""
        return f"workspace:{self.id}"


class Branch(UUIDModelMixin, TimestampedModelMixin, CachedModelMixin, ActiveModelMixin, models.Model):
    """Model for workspace branches in different locations"""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_branches')
    operating_hours = models.JSONField(default=dict, blank=True, help_text='Operating hours for each day of the week')
    images = models.JSONField(default=list, blank=True, help_text='List of branch photo URLs')
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'workspace_branch'
        ordering = ['-created_at']
        unique_together = ('workspace', 'name')

    def __str__(self):
        return f"{self.workspace.name} - {self.name}"
    
    def get_cache_key(self):
        """Generate cache key for this branch"""
        return f"branch:{self.id}"


class WorkspaceUser(UUIDModelMixin, TimestampedModelMixin, ActiveModelMixin, models.Model):
    """Model for workspace member relationships"""
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('user', 'User'),  # Regular user who books spaces
    )

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workspace_user'
        unique_together = ('workspace', 'user')
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.workspace.name} ({self.role})"


class Space(UUIDModelMixin, TimestampedModelMixin, CachedModelMixin, models.Model):
    """Model for bookable spaces within a workspace"""
    SPACE_TYPE_CHOICES = (
        ('meeting_room', 'Meeting Room'),
        ('office', 'Office'),
        ('coworking', 'Coworking Space'),
        ('event_space', 'Event Space'),
        ('desk', 'Dedicated Desk'),
        ('lounge', 'Lounge'),
    )

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='spaces')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    space_type = models.CharField(max_length=50, choices=SPACE_TYPE_CHOICES)
    capacity = models.IntegerField(validators=[MinValueValidator(1)])
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal('0'))])
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal('0'))])
    rules = models.TextField(blank=True, null=True, help_text='Usage rules and guidelines for the space')
    cancellation_policy = models.TextField(blank=True, null=True, help_text='Cancellation policy and refund rules')
    image_url = models.URLField(blank=True, null=True)
    amenities = models.JSONField(default=list, blank=True)  # List of amenities
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = 'workspace_space'
        ordering = ['name']
        unique_together = ('branch', 'name')

    def __str__(self):
        return f"{self.branch.name} - {self.name}"
    
    def get_cache_key(self):
        """Generate cache key for this space"""
        return f"space:{self.id}"


class SpaceCalendar(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """Model to manage space availability calendar"""
    
    BOOKING_TYPE_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
    ]
    
    space = models.OneToOneField(Space, on_delete=models.CASCADE, related_name='calendar')
    
    # Availability configuration
    time_interval_minutes = models.IntegerField(
        default=60,
        help_text='Time slot interval in minutes (e.g., 60 for hourly slots)'
    )
    
    # Operating hours per day (JSON format: {"0": {"start": "09:00", "end": "18:00"}, ...})
    operating_hours = models.JSONField(
        default=dict,
        blank=True,
        help_text='Operating hours by day (0=Sunday, 6=Saturday)'
    )
    
    # Booking types available
    hourly_enabled = models.BooleanField(default=True)
    daily_enabled = models.BooleanField(default=True)
    monthly_enabled = models.BooleanField(default=True)
    
    # Pricing per booking type
    hourly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    daily_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    monthly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Advance booking requirements (in days)
    min_advance_booking_days = models.IntegerField(
        default=0,
        help_text='Minimum days in advance to book'
    )
    max_advance_booking_days = models.IntegerField(
        default=365,
        help_text='Maximum days in advance to book'
    )
    
    class Meta:
        db_table = 'workspace_space_calendar'
    
    def __str__(self):
        return f"Calendar for {self.space.name}"


class SpaceCalendarSlot(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """Model to track individual calendar slots and their availability"""
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),  # Temporarily reserved during checkout
        ('booked', 'Booked'),
        ('blocked', 'Blocked'),
        ('maintenance', 'Maintenance'),
    ]
    
    calendar = models.ForeignKey(
        SpaceCalendar,
        on_delete=models.CASCADE,
        related_name='slots'
    )
    
    # Slot timing
    date = models.DateField(help_text='Date of the slot')
    start_time = models.TimeField(help_text='Start time of the slot')
    end_time = models.TimeField(help_text='End time of the slot')
    booking_type = models.CharField(
        max_length=20,
        choices=[('hourly', 'Hourly'), ('daily', 'Daily'), ('monthly', 'Monthly')],
        help_text='Type of booking for this slot'
    )
    
    # Availability
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )
    
    # Booking reference
    booking = models.ForeignKey(
        'booking.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_slots'
    )
    
    # Notes
    notes = models.TextField(blank=True, null=True, help_text='Reason for blocking/maintenance')
    
    class Meta:
        db_table = 'workspace_space_calendar_slot'
        ordering = ['date', 'start_time']
        unique_together = ('calendar', 'date', 'start_time', 'booking_type')
        indexes = [
            models.Index(fields=['calendar', 'date', 'status']),
            models.Index(fields=['booking']),
        ]
    
    def __str__(self):
        return f"{self.calendar.space.name} - {self.date} {self.start_time}-{self.end_time} ({self.status})"
