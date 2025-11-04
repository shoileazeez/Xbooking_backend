from django.db import models
from django.core.validators import MinValueValidator, URLValidator
from decimal import Decimal
from user.models import User
import uuid


class Workspace(models.Model):
    """Model for workspace/organization"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Branch(models.Model):
    """Model for workspace branches in different locations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_branch'
        ordering = ['-created_at']
        unique_together = ('workspace', 'name')

    def __str__(self):
        return f"{self.workspace.name} - {self.name}"


class WorkspaceUser(models.Model):
    """Model for workspace member relationships"""
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('user', 'User'),  # Regular user who books spaces
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_user'
        unique_together = ('workspace', 'user')
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.workspace.name} ({self.role})"


class Space(models.Model):
    """Model for bookable spaces within a workspace"""
    SPACE_TYPE_CHOICES = (
        ('meeting_room', 'Meeting Room'),
        ('office', 'Office'),
        ('coworking', 'Coworking Space'),
        ('event_space', 'Event Space'),
        ('desk', 'Dedicated Desk'),
        ('lounge', 'Lounge'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    operational_hours = models.JSONField(default=dict, blank=True, help_text='Operating hours for each day of the week')
    availability_schedule = models.JSONField(default=dict, blank=True, help_text='Custom availability schedule')
    image_url = models.URLField(blank=True, null=True)
    amenities = models.JSONField(default=list, blank=True)  # List of amenities
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_space'
        ordering = ['name']
        unique_together = ('branch', 'name')

    def __str__(self):
        return f"{self.branch.name} - {self.name}"
