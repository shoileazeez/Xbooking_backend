"""
User Preference Model - For storing user booking and space preferences
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
from core.mixins import UUIDModelMixin, TimestampedModelMixin
from user.models import User


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
        help_text='List of preferred space types (e.g., ["meeting_room", "office"])'
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
    
    preferred_locations = models.JSONField(
        default=list,
        blank=True,
        help_text='List of preferred location keywords or areas'
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
    
    # Notification Preferences (booking-related)
    notify_recommendations = models.BooleanField(
        default=True,
        help_text='Receive space recommendations based on preferences'
    )
    
    notify_price_drops = models.BooleanField(
        default=True,
        help_text='Notify when preferred spaces have price drops'
    )
    
    notify_new_spaces = models.BooleanField(
        default=True,
        help_text='Notify when new spaces matching preferences are added'
    )
    
    # Advanced Preferences
    auto_suggest_similar = models.BooleanField(
        default=True,
        help_text='Automatically suggest similar spaces based on booking history'
    )
    
    save_search_history = models.BooleanField(
        default=True,
        help_text='Save search history for better recommendations'
    )
    
    class Meta:
        db_table = 'user_preference'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Preferences for {self.user.email}"
