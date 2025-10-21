"""
Payment and Order Models
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from user.models import User
from workspace.models import Workspace
from booking.models import Booking
import uuid

# Import withdrawal models
from .withdrawal_models import BankAccount, Withdrawal, WithdrawalLog


class Order(models.Model):
    """Model for orders created from bookings"""
    
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    # Order details
    order_number = models.CharField(max_length=50, unique=True)
    bookings = models.ManyToManyField(Booking, related_name='orders')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    
    # Status
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    
    # Payment reference
    payment_method = models.CharField(max_length=50, blank=True, null=True)  # paystack, flutterwave, etc
    payment_reference = models.CharField(max_length=255, blank=True, null=True)  # transaction ID from payment gateway
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'payment_order'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['payment_reference']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        """Auto-generate order number if not exists"""
        if not self.order_number:
            # Generate order number: ORD-TIMESTAMP-RANDOM
            import time
            import random
            timestamp = str(int(time.time()))
            random_num = str(random.randint(1000, 9999))
            self.order_number = f"ORD-{timestamp[-6:]}-{random_num}"
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Model for payment transactions"""
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=3, default='NGN')  # Nigeria Naira
    
    # Payment gateway info
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    gateway_transaction_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Metadata from payment gateway
    gateway_response = models.JSONField(default=dict, blank=True)  # Store response from payment gateway
    
    # Retry info
    retry_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_retry_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'payment_payment'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order']),
            models.Index(fields=['gateway_transaction_id']),
        ]
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency} via {self.payment_method}"


class PaymentWebhook(models.Model):
    """Model for storing payment gateway webhooks"""
    
    WEBHOOK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_method = models.CharField(max_length=50)  # paystack, flutterwave, etc
    gateway_event_id = models.CharField(max_length=255, unique=True)
    
    # Webhook data
    payload = models.JSONField()  # Raw webhook payload from payment gateway
    
    # Processing
    status = models.CharField(max_length=20, choices=WEBHOOK_STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_webhook'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['payment_method', 'status']),
            models.Index(fields=['gateway_event_id']),
        ]
    
    def __str__(self):
        return f"Webhook {self.gateway_event_id} from {self.payment_method}"


class Refund(models.Model):
    """Model for refunds"""
    
    REFUND_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    REFUND_REASON_CHOICES = [
        ('user_request', 'User Request'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('system_error', 'System Error'),
        ('duplicate_charge', 'Duplicate Charge'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='refunds')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refunds')
    
    # Refund details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    reason = models.CharField(max_length=50, choices=REFUND_REASON_CHOICES)
    reason_description = models.TextField()
    
    # Gateway info
    gateway_refund_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='pending')
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'payment_refund'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['payment']),
        ]
    
    def __str__(self):
        return f"Refund {self.id} - {self.amount} NGN"
