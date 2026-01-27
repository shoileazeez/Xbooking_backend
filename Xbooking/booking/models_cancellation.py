"""
Booking Cancellation Models
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from user.models import User
from workspace.models import Workspace
from booking.models import Booking
from core.mixins import UUIDModelMixin, TimestampedModelMixin


class BookingCancellation(UUIDModelMixin, TimestampedModelMixin, models.Model):
    """Model for tracking booking cancellations with refund details"""
    
    CANCELLATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('refunded', 'Refunded'),
    ]
    
    CANCELLATION_REASON_CHOICES = [
        ('user_request', 'User Request'),
        ('change_of_plans', 'Change of Plans'),
        ('found_alternative', 'Found Alternative'),
        ('emergency', 'Emergency'),
        ('workspace_issue', 'Workspace Issue'),
        ('admin_cancellation', 'Admin Cancellation'),
        ('other', 'Other'),
    ]
    
    REFUND_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # Relationships
    booking = models.OneToOneField(
        Booking, 
        on_delete=models.CASCADE, 
        related_name='cancellation_detail'
    )
    cancelled_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='cancelled_bookings'
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_cancellations',
        help_text='Admin who approved the cancellation'
    )
    
    # Cancellation details
    reason = models.CharField(
        max_length=50,
        choices=CANCELLATION_REASON_CHOICES,
        default='user_request'
    )
    reason_description = models.TextField(
        help_text='Detailed reason for cancellation'
    )
    
    # Additional feedback fields for workspace improvement
    workspace_issues = models.JSONField(
        default=list,
        blank=True,
        help_text='List of issues experienced with the workspace'
    )
    found_alternative = models.BooleanField(
        default=False,
        help_text='Whether user found an alternative workspace'
    )
    alternative_reason = models.TextField(
        blank=True,
        null=True,
        help_text='What made the alternative workspace better'
    )
    would_book_again = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=[
            ('yes', 'Yes'),
            ('maybe', 'Maybe'),
            ('no', 'No')
        ],
        help_text='Whether user would book this workspace again'
    )
    suggestions = models.TextField(
        blank=True,
        null=True,
        help_text='User suggestions for workspace improvement'
    )
    rating_before_cancellation = models.IntegerField(
        null=True,
        blank=True,
        help_text='User rating before cancellation (1-5)'
    )
    contacted_workspace = models.BooleanField(
        default=False,
        help_text='Whether user contacted workspace before cancelling'
    )
    workspace_response_satisfactory = models.BooleanField(
        null=True,
        blank=True,
        help_text='Whether workspace response was satisfactory'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=CANCELLATION_STATUS_CHOICES,
        default='pending'
    )
    
    # Refund calculations
    original_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    refund_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Percentage of original amount to refund'
    )
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Actual refund amount'
    )
    penalty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Amount deducted as penalty'
    )
    
    # Refund status
    refund_status = models.CharField(
        max_length=20,
        choices=REFUND_STATUS_CHOICES,
        default='pending'
    )
    refund_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Transaction reference for refund'
    )
    
    # Timing details
    hours_until_checkin = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Hours between cancellation and check-in time'
    )
    cancelled_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    # Admin notes
    admin_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Internal notes from admin'
    )
    
    # Email tracking
    cancellation_email_sent = models.BooleanField(default=False)
    refund_email_sent = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'booking_cancellation'
        ordering = ['-cancelled_at']
        indexes = [
            models.Index(fields=['booking']),
            models.Index(fields=['cancelled_by', 'status']),
            models.Index(fields=['status', 'refund_status']),
            models.Index(fields=['-cancelled_at']),
        ]
    
    def __str__(self):
        return f"Cancellation {self.id} - Booking {self.booking.id} - {self.status}"
    
    @property
    def is_refundable(self):
        """Check if cancellation is eligible for refund"""
        return self.refund_amount > Decimal('0')
    
    @property
    def is_approved(self):
        """Check if cancellation is approved"""
        return self.status == 'approved'
    
    @property
    def is_refunded(self):
        """Check if refund is completed"""
        return self.refund_status == 'completed'
    
    @staticmethod
    def calculate_refund_policy(hours_until_checkin, original_amount):
        """
        Calculate refund based on cancellation policy:
        - 100% refund if cancelled 24+ hours before check-in
        - 50% refund if cancelled 6-24 hours before check-in
        - 0% refund if cancelled less than 6 hours before check-in
        
        Args:
            hours_until_checkin: Hours between now and check-in time
            original_amount: Original booking amount
            
        Returns:
            tuple: (refund_percentage, refund_amount, penalty_amount)
        """
        hours = Decimal(str(hours_until_checkin))
        
        if hours >= 24:
            # Full refund
            refund_percentage = Decimal('100.00')
            refund_amount = original_amount
            penalty_amount = Decimal('0.00')
        elif hours >= 6:
            # 50% refund
            refund_percentage = Decimal('50.00')
            refund_amount = original_amount * Decimal('0.5')
            penalty_amount = original_amount * Decimal('0.5')
        else:
            # No refund
            refund_percentage = Decimal('0.00')
            refund_amount = Decimal('0.00')
            penalty_amount = original_amount
        
        return (refund_percentage, refund_amount, penalty_amount)
