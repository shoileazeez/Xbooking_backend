"""
Booking and Cart Models
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from user.models import User
from workspace.models import Space, Workspace
import uuid
import secrets
import string
from django.utils import timezone
from datetime import time

def generate_verification_code():
    """Generate a unique verification code for guests"""
    chars = string.ascii_uppercase + string.digits
    return 'G-' + ''.join(secrets.choice(chars) for _ in range(10))

def default_start_time():
    """Default start time for bookings"""
    return time(9, 0)  # 9:00 AM

def default_end_time():
    """Default end time for bookings"""
    return time(17, 0)  # 5:00 PM


class Booking(models.Model):
    """Model for space bookings"""
    
    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    BOOKING_TYPE_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='bookings')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    
    # Booking details
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES, default='daily')
    
    # Booking date and time (from calendar)
    booking_date = models.DateField(help_text='Date of the booking', default=timezone.now)
    start_time = models.TimeField(help_text='Start time of the booking', default=default_start_time)
    end_time = models.TimeField(help_text='End time of the booking', default=default_end_time)
    
    # Full datetime fields (computed from date + time)
    check_in = models.DateTimeField(help_text='Check-in datetime')
    check_out = models.DateTimeField(help_text='Check-out datetime')
    slot = models.ForeignKey('workspace.SpaceCalendarSlot', on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    
    number_of_guests = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    
    # Check-in/out tracking
    is_checked_in = models.BooleanField(default=False, help_text='Whether user has checked in')
    is_checked_out = models.BooleanField(default=False, help_text='Whether user has checked out')
    
    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])
    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    
    # Status
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='pending')
    
    # Special requests
    special_requests = models.TextField(blank=True, null=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    
    # Email reminder tracking
    reminder_sent = models.BooleanField(default=False, help_text='Whether check-in reminder email was sent')
    reminder_sent_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'booking_booking'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['check_in', 'check_out']),
            models.Index(fields=['booking_date']),
        ]
    
    def __str__(self):
        return f"Booking {self.id} - {self.space.name} by {self.user.email}"
    
    @property
    def days_used(self):
        """Calculate days used for monthly bookings"""
        if self.booking_type != 'monthly':
            return None
        if not self.is_checked_in:
            return 0
        from django.utils import timezone
        from datetime import timedelta
        
        end_date = timezone.now().date() if not self.is_checked_out else self.check_out.date()
        start_date = self.check_in.date()
        return (end_date - start_date).days + 1
    
    @property
    def days_remaining(self):
        """Calculate days remaining for monthly bookings"""
        if self.booking_type != 'monthly':
            return None
        from datetime import timedelta
        total_days = (self.check_out.date() - self.check_in.date()).days + 1
        used = self.days_used or 0
        return total_days - used


class Reservation(models.Model):
    """Temporary reservation/hold for a specific space slot.

    Reservations are used to hold a slot while a user completes payment.
    They should be created when a user selects a slot and expire after a short period.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('held', 'Held'),
        ('purchased', 'Purchased'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='reservations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    start = models.DateTimeField()
    end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'booking_reservation'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reservation {self.id} - {self.space.name} ({self.start} - {self.end})"


class Cart(models.Model):
    """Model for shopping cart"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    # Cart is now per-user (can contain items from multiple workspaces)
    
    # Pricing totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    discount_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    tax_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    
    item_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'booking_cart'
        # unique per user only
    
    def __str__(self):
        return f"Cart {self.id} - {self.user.email}"
    
    def calculate_totals(self):
        """Recalculate cart totals"""
        items = self.items.all()
        self.subtotal = sum(item.price for item in items)
        self.discount_total = sum(item.discount_amount for item in items)
        self.tax_total = sum(item.tax_amount for item in items)
        self.total = self.subtotal - self.discount_total + self.tax_total
        self.item_count = items.count()
        self.save()


class CartItem(models.Model):
    """Model for items in shopping cart"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='cart_items')
    # Optional reservation hold for this cart item
    reservation = models.ForeignKey('Reservation', on_delete=models.SET_NULL, null=True, blank=True, related_name='cart_items')
    
    # Booking details with calendar info
    booking_date = models.DateField(help_text='Date of the booking', default=timezone.now)
    start_time = models.TimeField(help_text='Start time of the booking', default=default_start_time)
    end_time = models.TimeField(help_text='End time of the booking', default=default_end_time)
    booking_type = models.CharField(
        max_length=20,
        choices=[('hourly', 'Hourly'), ('daily', 'Daily'), ('monthly', 'Monthly')],
        default='daily'
    )
    
    # Full datetime fields
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    slot = models.ForeignKey('workspace.SpaceCalendarSlot', on_delete=models.SET_NULL, null=True, blank=True, related_name='cart_items')
    number_of_guests = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])
    
    # Special requests
    special_requests = models.TextField(blank=True, null=True)
    
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'booking_cart_item'
        unique_together = ('cart', 'space', 'booking_date', 'start_time', 'end_time', 'booking_type')
    
    def __str__(self):
        return f"CartItem - {self.space.name} on {self.booking_date}"


class BookingReview(models.Model):
    """Model for booking reviews and ratings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booking_reviews')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='reviews')
    
    rating = models.IntegerField(validators=[MinValueValidator(1)], help_text='Rating from 1-5')
    comment = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'booking_review'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review for {self.space.name} - {self.rating}★"


class Guest(models.Model):
    """Model for booking guests with QR code verification"""
    
    GUEST_STATUS_CHOICES = [
        ('pending', 'Pending - QR code sent'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
    ]
    

    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='guests')
    
    # Guest information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=GUEST_STATUS_CHOICES, default='pending')
    
    # QR Code tracking
    qr_code_sent = models.BooleanField(default=False)
    qr_code_sent_at = models.DateTimeField(blank=True, null=True)
    qr_code_verification_code = models.CharField(max_length=50, unique=True, default=generate_verification_code, help_text='Unique verification code for guest QR')
    
    # Email tracking
    reminder_sent = models.BooleanField(default=False, help_text='Whether check-in reminder email was sent')
    reminder_sent_at = models.DateTimeField(blank=True, null=True)
    receipt_sent = models.BooleanField(default=False, help_text='Whether checkout receipt email was sent')
    receipt_sent_at = models.DateTimeField(blank=True, null=True)
    
    # Check-in/out tracking
    checked_in_at = models.DateTimeField(blank=True, null=True)
    checked_out_at = models.DateTimeField(blank=True, null=True)
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='checked_in_guests')
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'booking_guest'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['email']),
            models.Index(fields=['qr_code_verification_code']),
        ]
    
    def __str__(self):
        return f"Guest {self.first_name} {self.last_name} - {self.booking.id}"


class Checkout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='checkout')
    bookings = models.ManyToManyField(Booking, related_name='checkouts', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'booking_checkout'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Checkout {self.id} - {self.user.email}"
