"""
Payment and Order Admin Configuration
"""
from django.contrib import admin
from payment.models import Order, Payment, PaymentWebhook, Refund


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin for Order model"""
    list_display = ['order_number', 'user', 'total_amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__email']
    readonly_fields = ['id', 'order_number', 'created_at', 'updated_at', 'paid_at', 'completed_at']
    fieldsets = (
        ('Order Info', {
            'fields': ('id', 'order_number', 'workspace', 'user')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'discount_amount', 'tax_amount', 'total_amount')
        }),
        ('Payment', {
            'fields': ('status', 'payment_method', 'payment_reference')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at', 'completed_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        })
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin for Payment model"""
    list_display = ['id', 'order', 'amount', 'currency', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'currency', 'created_at']
    search_fields = ['order__order_number', 'gateway_transaction_id', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at']
    fieldsets = (
        ('Payment Info', {
            'fields': ('id', 'order', 'workspace', 'user')
        }),
        ('Amount', {
            'fields': ('amount', 'currency')
        }),
        ('Gateway', {
            'fields': ('payment_method', 'gateway_transaction_id', 'gateway_response')
        }),
        ('Status', {
            'fields': ('status', 'retry_count', 'last_retry_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        })
    )


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    """Admin for PaymentWebhook model"""
    list_display = ['gateway_event_id', 'payment_method', 'status', 'received_at']
    list_filter = ['payment_method', 'status', 'received_at']
    search_fields = ['gateway_event_id']
    readonly_fields = ['id', 'received_at']
    fieldsets = (
        ('Webhook Info', {
            'fields': ('id', 'payment_method', 'gateway_event_id')
        }),
        ('Payload', {
            'fields': ('payload',)
        }),
        ('Processing', {
            'fields': ('status', 'processed_at', 'error_message')
        }),
        ('Received', {
            'fields': ('received_at',)
        })
    )


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """Admin for Refund model"""
    list_display = ['id', 'payment', 'amount', 'reason', 'status', 'requested_at']
    list_filter = ['reason', 'status', 'requested_at']
    search_fields = ['payment__order__order_number', 'user__email']
    readonly_fields = ['id', 'requested_at']
    fieldsets = (
        ('Refund Info', {
            'fields': ('id', 'payment', 'order', 'workspace', 'user')
        }),
        ('Amount', {
            'fields': ('amount',)
        }),
        ('Reason', {
            'fields': ('reason', 'reason_description')
        }),
        ('Gateway', {
            'fields': ('gateway_refund_id',)
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'completed_at')
        })
    )
