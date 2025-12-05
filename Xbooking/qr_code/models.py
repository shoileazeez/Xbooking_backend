"""
QR Code generation and management
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from payment.models import Order
from booking.models import Booking
import uuid


class OrderQRCode(models.Model):
    """Model for storing generated QR codes for orders (DEPRECATED - use BookingQRCode)"""
    
    QR_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('sent', 'Sent to User'),
        ('scanned', 'Scanned'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='qr_code')
    
    # QR Code data
    qr_code_data = models.TextField()  # The encoded QR data
    
    # Appwrite storage
    qr_code_image_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to QR code image stored in Appwrite"
    )
    appwrite_file_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="File ID in Appwrite storage"
    )
    
    # Verification details
    verification_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for QR verification"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=QR_STATUS_CHOICES,
        default='pending'
    )
    
    # Scan tracking
    scan_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_scanned_at = models.DateTimeField(blank=True, null=True)
    scanned_by_ip = models.CharField(max_length=100, blank=True, null=True)
    
    # Verification tracking
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_qr_codes'
    )
    
    # Expiry
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="QR code expiry time for check-in"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'qr_code_order_qrcode'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['verification_code']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"QR Code for Order {self.order.order_number}"


class BookingQRCode(models.Model):
    """Model for storing generated QR codes per booking"""
    
    QR_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('sent', 'Sent to User'),
        ('scanned', 'Scanned'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='qr_code')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='booking_qr_codes', null=True, blank=True)
    
    # QR Code data
    qr_code_data = models.TextField()  # The encoded QR data
    
    # Appwrite storage
    qr_code_image_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to QR code image stored in Appwrite"
    )
    appwrite_file_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="File ID in Appwrite storage"
    )
    
    # Verification details
    verification_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for QR verification"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=QR_STATUS_CHOICES,
        default='pending'
    )
    
    # Usage tracking
    used = models.BooleanField(
        default=False,
        help_text="True after booking is completed/checked out"
    )
    total_check_ins = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total check-in events (for monthly bookings)"
    )
    max_check_ins = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum check-ins allowed (for monthly bookings)"
    )
    
    # Scan tracking
    scan_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_scanned_at = models.DateTimeField(blank=True, null=True)
    scanned_by_ip = models.CharField(max_length=100, blank=True, null=True)
    
    # Verification tracking
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_booking_qr_codes'
    )
    
    # Expiry - based on booking checkout time
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="QR code expiry time (usually checkout time)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'qr_code_booking_qrcode'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking']),
            models.Index(fields=['order']),
            models.Index(fields=['verification_code']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        """Set expires_at to booking check_out time if not already set"""
        if not self.expires_at and self.booking:
            self.expires_at = self.booking.check_out
        super().save(*args, **kwargs)
    
    def calculate_max_check_ins(self):
        """
        Calculate maximum check-ins based on booking type and dates
        - For hourly/daily: 1 check-in
        - For monthly: number of days in the booking month (28/30/31)
        """
        from calendar import monthrange
        
        if self.booking.booking_type == 'monthly':
            year = self.booking.check_in.year
            month = self.booking.check_in.month
            days_in_month = monthrange(year, month)[1]
            return days_in_month
        else:
            return 1
    
    def __str__(self):
        return f"QR Code for Booking {self.booking.id} - {self.booking.space.name}"


class CheckIn(models.Model):
    """Model to track each check-in/check-out event for a booking"""
    
    CHECK_IN_STATUS_CHOICES = [
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='check_ins')
    qr_code = models.ForeignKey(BookingQRCode, on_delete=models.CASCADE, related_name='check_ins')
    
    # Check-in/out times
    check_in_time = models.DateTimeField(help_text="When the user checked in")
    check_out_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the user checked out"
    )
    
    # Duration (auto-calculated)
    duration = models.DurationField(
        blank=True,
        null=True,
        help_text="Duration of stay (auto-calculated after checkout)"
    )
    
    # Verification
    verified_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_check_ins'
    )
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=CHECK_IN_STATUS_CHOICES,
        default='checked_in'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'qr_code_check_in'
        ordering = ['-check_in_time']
        indexes = [
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['qr_code']),
            models.Index(fields=['check_in_time']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-calculate duration if both check-in and check-out times exist"""
        if self.check_in_time and self.check_out_time:
            self.duration = self.check_out_time - self.check_in_time
            self.status = 'checked_out'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"CheckIn for Booking {self.booking.id} at {self.check_in_time}"


class BookingQRCodeMixin:
    """Mixin for BookingQRCode to calculate max check-ins based on booking type"""
    
    @staticmethod
    def calculate_max_check_ins(booking):
        """
        Calculate maximum check-ins based on booking type and dates
        - For hourly/daily: 1 check-in
        - For monthly: number of days in the booking month (28/30/31)
        """
        if booking.booking_type == 'monthly':
            # Get the month from the booking check_in date
            from calendar import monthrange
            year = booking.check_in.year
            month = booking.check_in.month
            days_in_month = monthrange(year, month)[1]
            return days_in_month
        else:
            # Hourly/daily bookings only have one check-in
            return 1


class BookingQRCodeLog(models.Model):
    """Log of QR code scans"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    qr_code = models.ForeignKey(
        OrderQRCode,
        on_delete=models.CASCADE,
        related_name='scan_logs'
    )
    
    # Scan details
    scanned_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='qr_code_scans'
    )
    scan_device_ip = models.CharField(max_length=100, blank=True, null=True)
    scan_device_user_agent = models.TextField(blank=True, null=True)
    
    # Result
    scan_result = models.CharField(
        max_length=50,
        choices=[
            ('success', 'Success'),
            ('invalid', 'Invalid'),
            ('expired', 'Expired'),
            ('already_verified', 'Already Verified'),
        ],
        default='success'
    )
    
    # Timestamps
    scanned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'qr_code_scan_log'
        ordering = ['-scanned_at']
        indexes = [
            models.Index(fields=['qr_code', 'scanned_at']),
            models.Index(fields=['scanned_by']),
        ]
    
    def __str__(self):
        return f"Scan of {self.qr_code.verification_code} by {self.scanned_by}"

