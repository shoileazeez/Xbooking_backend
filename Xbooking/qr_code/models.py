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
    qr_code_image = models.ImageField(
        upload_to='qr_codes/',
        blank=True,
        null=True,
        help_text="Generated QR code image"
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
    qr_code_image = models.ImageField(
        upload_to='qr_codes/bookings/',
        blank=True,
        null=True,
        help_text="Generated QR code image"
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
    
    def __str__(self):
        return f"QR Code for Booking {self.booking.id} - {self.booking.space.name}"


class QRCodeScanLog(models.Model):
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

