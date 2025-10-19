"""
QR Code Admin Configuration
"""
from django.contrib import admin
from qr_code.models import OrderQRCode, QRCodeScanLog, NotificationPreference, Notification


@admin.register(OrderQRCode)
class OrderQRCodeAdmin(admin.ModelAdmin):
    """Admin for OrderQRCode model"""
    list_display = ['verification_code', 'order', 'status', 'verified', 'scan_count', 'created_at']
    list_filter = ['status', 'verified', 'created_at']
    search_fields = ['verification_code', 'order__order_number']
    readonly_fields = ['id', 'verification_code', 'scan_count', 'created_at', 'updated_at']
    fieldsets = (
        ('QR Code Info', {
            'fields': ('id', 'order', 'verification_code', 'qr_code_image')
        }),
        ('Data', {
            'fields': ('qr_code_data',)
        }),
        ('Status', {
            'fields': ('status', 'verified', 'verified_by', 'verified_at')
        }),
        ('Scan Info', {
            'fields': ('scan_count', 'last_scanned_at', 'scanned_by_ip')
        }),
        ('Expiry', {
            'fields': ('expires_at',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'sent_at')
        })
    )


@admin.register(QRCodeScanLog)
class QRCodeScanLogAdmin(admin.ModelAdmin):
    """Admin for QRCodeScanLog model"""
    list_display = ['verification_code', 'scanned_by', 'scan_result', 'scanned_at']
    list_filter = ['scan_result', 'scanned_at']
    search_fields = ['qr_code__verification_code', 'scanned_by__email']
    readonly_fields = ['id', 'scanned_at']
    
    def verification_code(self, obj):
        return obj.qr_code.verification_code
    verification_code.short_description = 'QR Code'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin for NotificationPreference model"""
    list_display = ['user', 'email_order_confirmation', 'email_payment_confirmation', 'email_qr_code']
    list_filter = ['email_order_confirmation', 'email_payment_confirmation', 'email_qr_code']
    search_fields = ['user__email']
    readonly_fields = ['id']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for Notification model"""
    list_display = ['title', 'user', 'notification_type', 'channel', 'is_sent', 'is_read', 'created_at']
    list_filter = ['notification_type', 'channel', 'is_sent', 'is_read', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    readonly_fields = ['id', 'created_at']
    fieldsets = (
        ('Notification Info', {
            'fields': ('id', 'user', 'notification_type', 'channel')
        }),
        ('Content', {
            'fields': ('title', 'message', 'data')
        }),
        ('Status', {
            'fields': ('is_sent', 'is_read', 'send_error')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at', 'read_at')
        })
    )
