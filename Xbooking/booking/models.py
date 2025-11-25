"""
Booking and Cart Models
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from user.models import User
from workspace.models import Space, Workspace
import uuid


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
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    number_of_guests = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    
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
    
    class Meta:
        db_table = 'booking_booking'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['check_in', 'check_out']),
        ]
    
    def __str__(self):
        return f"Booking {self.id} - {self.space.name} by {self.user.email}"


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
    
    # Booking details
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
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
        unique_together = ('cart', 'space', 'check_in', 'check_out')
    
    def __str__(self):
        return f"CartItem - {self.space.name}"


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


class BookingAvailability(models.Model):
    """Model to track space availability for faster queries"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space = models.OneToOneField(Space, on_delete=models.CASCADE, related_name='availability')
    
    available_from = models.DateTimeField()
    available_until = models.DateTimeField()
    is_available = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'booking_availability'
    
    def __str__(self):
        return f"Availability - {self.space.name}"


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
    qr_code_verification_code = models.CharField(max_length=50, unique=True, help_text='Unique verification code for guest QR')
    
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

