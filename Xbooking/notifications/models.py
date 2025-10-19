"""
Notification models
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
import uuid

User = get_user_model()


class NotificationPreference(models.Model):
    """User notification preferences"""
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_enabled = models.BooleanField(default=True)
    email_qr_code = models.BooleanField(default=True, help_text='Send QR codes via email')
    email_order_confirmation = models.BooleanField(default=True)
    email_payment_confirmation = models.BooleanField(default=True)
    email_booking_reminder = models.BooleanField(default=True)
    email_booking_update = models.BooleanField(default=True)
    
    # SMS preferences
    sms_enabled = models.BooleanField(default=False)
    sms_qr_code = models.BooleanField(default=False)
    sms_booking_reminder = models.BooleanField(default=False)
    
    # Push notification preferences
    push_enabled = models.BooleanField(default=False)
    push_qr_code = models.BooleanField(default=False)
    push_booking_reminder = models.BooleanField(default=False)
    push_booking_update = models.BooleanField(default=False)
    
    # In-app preferences
    in_app_enabled = models.BooleanField(default=True)
    in_app_qr_code = models.BooleanField(default=True)
    in_app_booking_reminder = models.BooleanField(default=True)
    in_app_booking_update = models.BooleanField(default=True)
    
    # Frequency
    FREQUENCY_CHOICES = [
        ('immediate', 'Immediate'),
        ('daily_digest', 'Daily Digest'),
        ('weekly_digest', 'Weekly Digest'),
    ]
    digest_frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='immediate')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
        db_table = 'notification_preferences'
    
    def __str__(self):
        return f"Notification Preferences for {self.user.email}"


class Notification(models.Model):
    """Notification model - stores all notifications sent to users"""
    
    NOTIFICATION_TYPES = [
        ('qr_code_generated', 'QR Code Generated'),
        ('qr_code_expired', 'QR Code Expired'),
        ('order_created', 'Order Created'),
        ('payment_successful', 'Payment Successful'),
        ('payment_failed', 'Payment Failed'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('booking_reminder', 'Booking Reminder'),
        ('booking_check_in', 'Check-in Reminder'),
        ('booking_completed', 'Booking Completed'),
        ('refund_initiated', 'Refund Initiated'),
        ('refund_completed', 'Refund Completed'),
        ('system_alert', 'System Alert'),
    ]
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    
    # Content
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True, help_text='Additional data (e.g., order_id, qr_code_id)')
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    is_clicked = models.BooleanField(default=False, help_text='For push notifications')
    
    # Tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_read', 'user']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class NotificationLog(models.Model):
    """Log for tracking notification delivery attempts"""
    
    DELIVERY_STATUS = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
        ('complained', 'Complained'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='delivery_logs')
    
    status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='pending')
    attempt_number = models.PositiveIntegerField(default=1)
    
    # Error tracking
    error_message = models.TextField(blank=True, help_text='Error message if delivery failed')
    response_code = models.CharField(max_length=50, blank=True, help_text='HTTP or gateway response code')
    
    # Timestamps
    attempted_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        db_table = 'notification_logs'
        indexes = [
            models.Index(fields=['notification', '-attempted_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Delivery Log - {self.notification.id} ({self.status})"


class BroadcastNotification(models.Model):
    """Broadcast notifications for admins/managers to send to workspace users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey('workspace.Workspace', on_delete=models.CASCADE, related_name='broadcast_notifications')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='broadcast_notifications_sent')
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    channels = models.JSONField(default=list, help_text='List of channels to send to: ["email", "push", "in_app"]')
    
    # Targeting
    target_users = models.ManyToManyField(User, related_name='broadcast_notifications_received', blank=True, help_text='Leave empty to send to all workspace users')
    target_roles = models.JSONField(default=list, help_text='Target specific roles: ["admin", "manager", "staff", "user"]')
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Stats
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    read_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Broadcast Notification'
        verbose_name_plural = 'Broadcast Notifications'
        db_table = 'broadcast_notifications'
        indexes = [
            models.Index(fields=['workspace', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.workspace.name}"
