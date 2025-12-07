"""
QR Code Admin Configuration
"""
from django.contrib import admin
from qr_code.models import OrderQRCode, BookingQRCode, CheckIn, BookingQRCodeLog


@admin.register(OrderQRCode)
class OrderQRCodeAdmin(admin.ModelAdmin):
    """Admin for OrderQRCode model"""
    list_display = ['verification_code', 'order', 'status', 'verified', 'scan_count', 'created_at']
    list_filter = ['status', 'verified', 'created_at']
    search_fields = ['verification_code', 'order__order_number']
    readonly_fields = ['id', 'verification_code', 'scan_count', 'created_at', 'updated_at', 'appwrite_file_id']
    fieldsets = (
        ('QR Code Info', {
            'fields': ('id', 'order', 'verification_code')
        }),
        ('Appwrite Storage', {
            'fields': ('qr_code_image_url', 'appwrite_file_id')
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


@admin.register(BookingQRCode)
class BookingQRCodeAdmin(admin.ModelAdmin):
    """Admin for BookingQRCode model"""
    list_display = ['verification_code', 'booking', 'status', 'used', 'total_check_ins', 'max_check_ins', 'created_at']
    list_filter = ['status', 'used', 'created_at', 'booking__booking_type']
    search_fields = ['verification_code', 'booking__id', 'booking__user__email']
    readonly_fields = ['id', 'verification_code', 'total_check_ins', 'created_at', 'sent_at', 'appwrite_file_id']
    
    fieldsets = (
        ('QR Code Info', {
            'fields': ('id', 'booking', 'order', 'verification_code')
        }),
        ('Appwrite Storage', {
            'fields': ('qr_code_image_url', 'appwrite_file_id')
        }),
        ('Status', {
            'fields': ('status', 'used')
        }),
        ('Check-in Tracking', {
            'fields': ('total_check_ins', 'max_check_ins')
        }),
        ('Scan Info', {
            'fields': ('scan_count', 'last_scanned_at', 'scanned_by_ip')
        }),
        ('Verification', {
            'fields': ('verified', 'verified_at', 'verified_by')
        }),
        ('Expiry', {
            'fields': ('expires_at',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at')
        })
    )


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    """Admin for CheckIn model"""
    list_display = ['booking', 'check_in_time', 'check_out_time', 'verified_by', 'created_at']
    list_filter = ['created_at', 'verified_by']
    search_fields = ['booking__id', 'verified_by__email']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Check-in Info', {
            'fields': ('id', 'booking', 'qr_code')
        }),
        ('Times', {
            'fields': ('check_in_time', 'check_out_time', 'duration')
        }),
        ('Verification', {
            'fields': ('verified_by', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )


@admin.register(BookingQRCodeLog)
class BookingQRCodeLogAdmin(admin.ModelAdmin):
    """Admin for BookingQRCodeLog model"""
    list_display = ['qr_code', 'scan_result', 'scanned_by']
    list_filter = ['scan_result', 'scanned_by']
    search_fields = ['qr_code__verification_code']
    readonly_fields = ['id']