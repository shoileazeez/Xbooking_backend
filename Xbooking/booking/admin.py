from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from datetime import timedelta
from booking.models import Booking, Cart, CartItem, BookingReview, Reservation, Checkout


class CartItemInline(admin.TabularInline):
    """Inline admin for CartItems"""
    model = CartItem
    extra = 0
    fields = ['space', 'check_in', 'check_out', 'price', 'added_at']
    readonly_fields = ['added_at', 'updated_at']
    can_delete = True


class BookingReviewInline(admin.TabularInline):
    """Inline admin for BookingReviews"""
    model = BookingReview
    extra = 0
    fields = ['rating', 'comment', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_id_display',
        'user_display',
        'space_display',
        'status_display',
        'date_range',
        'total_price_display',
        'booking_type_display',
        'created_at'
    ]
    list_filter = ['status', 'booking_type', 'created_at', 'check_in', 'confirmed_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'space__name', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'confirmed_at', 'cancelled_at', 'pricing_summary']
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('id', 'user', 'space', 'workspace', 'booking_type', 'status')
        }),
        ('Reservation Details', {
            'fields': ('check_in', 'check_out', 'special_requests')
        }),
        ('Pricing', {
            'fields': ('base_price', 'discount_amount', 'tax_amount', 'total_price', 'pricing_summary'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('confirmed_at', 'cancelled_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [BookingReviewInline]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    actions = ['mark_confirmed', 'mark_pending', 'mark_completed', 'mark_cancelled', 'export_bookings']
    
    def booking_id_display(self, obj):
        return str(obj.id)[:8]
    booking_id_display.short_description = 'Booking ID'
    
    def user_display(self, obj):
        return f"{obj.user.email}"
    user_display.short_description = 'User'
    
    def space_display(self, obj):
        return f"{obj.space.name}"
    space_display.short_description = 'Space'
    
    def status_display(self, obj):
        colors = {
            'pending': '#FF9800',
            'confirmed': '#4CAF50',
            'in_progress': '#2196F3',
            'completed': '#8BC34A',
            'cancelled': '#F44336'
        }
        color = colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def booking_type_display(self, obj):
        badge_colors = {
            'direct': '#E3F2FD',
            'from_cart': '#F3E5F5'
        }
        text_colors = {
            'direct': '#1976D2',
            'from_cart': '#7B1FA2'
        }
        color_bg = badge_colors.get(obj.booking_type, '#F5F5F5')
        color_text = text_colors.get(obj.booking_type, '#424242')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 6px; border-radius: 2px; font-size: 0.85em;">{}</span>',
            color_bg,
            color_text,
            obj.get_booking_type_display()
        )
    booking_type_display.short_description = 'Type'
    
    def date_range(self, obj):
        duration = obj.check_out - obj.check_in
        hours = duration.total_seconds() / 3600
        return f"{obj.check_in.strftime('%m/%d %H:%M')} - {obj.check_out.strftime('%H:%M')} ({hours:.1f}h)"
    date_range.short_description = 'Reservation'
    
    def total_price_display(self, obj):
        return f"₦{obj.total_price:,.2f}"
    total_price_display.short_description = 'Total Price'
    
    def pricing_summary(self, obj):
        return format_html(
            '<div style="line-height: 1.8;">'
            '<strong>Base Price:</strong> ₦{:,.2f}<br/>'
            '<strong>Discount:</strong> -₦{:,.2f}<br/>'
            '<strong>Tax:</strong> +₦{:,.2f}<br/>'
            '<strong style="font-size: 1.1em; color: green;">Total:</strong> <strong style="font-size: 1.1em; color: green;">₦{:,.2f}</strong>'
            '</div>',
            obj.base_price,
            obj.discount_amount,
            obj.tax_amount,
            obj.total_price
        )
    pricing_summary.short_description = 'Pricing Breakdown'
    
    def mark_confirmed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='confirmed', confirmed_at=timedelta())
        self.message_user(request, f'{updated} booking(s) marked as confirmed.')
    mark_confirmed.short_description = 'Mark selected as Confirmed'
    
    def mark_pending(self, request, queryset):
        updated = queryset.update(status='pending', confirmed_at=None)
        self.message_user(request, f'{updated} booking(s) marked as Pending.')
    mark_pending.short_description = 'Mark selected as Pending'
    
    def mark_completed(self, request, queryset):
        updated = queryset.filter(status__in=['confirmed', 'in_progress']).update(status='completed')
        self.message_user(request, f'{updated} booking(s) marked as Completed.')
    mark_completed.short_description = 'Mark selected as Completed'
    
    def mark_cancelled(self, request, queryset):
        from django.utils import timezone
        updated = queryset.exclude(status='cancelled').update(status='cancelled', cancelled_at=timezone.now())
        self.message_user(request, f'{updated} booking(s) cancelled.')
    mark_cancelled.short_description = 'Cancel selected bookings'
    
    def export_bookings(self, request, queryset):
        """Placeholder for CSV export functionality"""
        self.message_user(request, f'Export functionality - {queryset.count()} bookings selected.')
    export_bookings.short_description = 'Export selected bookings to CSV'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'space', 'workspace')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['cart_id_display', 'user_display', 'item_count_display', 'total_display', 'last_updated']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'cart_summary']
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('id', 'user')
        }),
        ('Cart Summary', {
            'fields': ('item_count_display', 'total_display', 'cart_summary'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CartItemInline]
    ordering = ['-updated_at']
    actions = ['clear_carts', 'view_cart_items']
    
    def cart_id_display(self, obj):
        return str(obj.id)[:8]
    cart_id_display.short_description = 'Cart ID'
    
    def user_display(self, obj):
        return f"{obj.user.full_name or obj.user.email}"
    user_display.short_description = 'User'
    

    
    def item_count_display(self, obj):
        count = obj.items.count()
        color = '#4CAF50' if count > 0 else '#BDBDBD'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px;">{} items</span>',
            color,
            count
        )
    item_count_display.short_description = 'Items'
    
    def total_display(self, obj):
        return f"₦{obj.total:,.2f}"
    total_display.short_description = 'Total'
    
    def last_updated(self, obj):
        from django.utils.timesince import timesince
        return f"{timesince(obj.updated_at)} ago"
    last_updated.short_description = 'Last Updated'
    
    def cart_summary(self, obj):
        items = obj.items.all()
        item_list = '<br/>'.join([
            f"• {item.space.name}: {item.check_in.strftime('%m/%d %H:%M')} - {item.check_out.strftime('%H:%M')} (₦{item.price:,.2f})"
            for item in items
        ]) if items.exists() else '<em>No items</em>'
        
        return format_html(
            '<div style="line-height: 1.8;">'
            '<strong>Items in Cart:</strong><br/>{}<br/><br/>'
            '<strong style="font-size: 1.1em; color: green;">Total: ₦{:,.2f}</strong>'
            '</div>',
            item_list,
            obj.total
        )
    cart_summary.short_description = 'Cart Summary'
    
    def clear_carts(self, request, queryset):
        for cart in queryset:
            cart.items.all().delete()
        self.message_user(request, f'Cleared items from {queryset.count()} cart(s).')
    clear_carts.short_description = 'Clear selected carts'
    
    def view_cart_items(self, request, queryset):
        self.message_user(request, f'View cart items for {queryset.count()} cart(s).')
    view_cart_items.short_description = 'View cart items'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('items')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['item_id_display', 'space_display', 'user_display', 'time_range', 'price_display', 'status_display', 'added_at']
    list_filter = ['added_at', 'updated_at']
    search_fields = ['space__name', 'cart__user__email']
    readonly_fields = ['id', 'added_at', 'updated_at']
    
    fieldsets = (
        ('Item Information', {
            'fields': ('id', 'cart', 'space')
        }),
        ('Reservation', {
            'fields': ('check_in', 'check_out')
        }),
        ('Pricing', {
            'fields': ('price',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('added_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-added_at']
    date_hierarchy = 'added_at'
    
    def item_id_display(self, obj):
        return str(obj.id)[:8]
    item_id_display.short_description = 'Item ID'
    
    def space_display(self, obj):
        return obj.space.name
    space_display.short_description = 'Space'
    
    def user_display(self, obj):
        return obj.cart.user.email
    user_display.short_description = 'User'
    
    def time_range(self, obj):
        duration = obj.check_out - obj.check_in
        hours = duration.total_seconds() / 3600
        return f"{obj.check_in.strftime('%m/%d %H:%M')} - {obj.check_out.strftime('%H:%M')} ({hours:.1f}h)"
    time_range.short_description = 'Time Slot'
    
    def price_display(self, obj):
        return f"₦{obj.price:,.2f}"
    price_display.short_description = 'Price'
    
    def status_display(self, obj):
        return format_html(
            '<span style="background-color: #FFC107; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">In Cart</span>'
        )
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('cart', 'space', 'cart__user')


@admin.register(BookingReview)
class BookingReviewAdmin(admin.ModelAdmin):
    list_display = ['review_id_display', 'space_display', 'user_display', 'rating_display', 'comment_preview', 'created_at']
    list_filter = ['rating', 'created_at', 'booking__workspace']
    search_fields = ['space__name', 'user__email', 'comment']
    readonly_fields = ['id', 'created_at', 'updated_at', 'full_comment']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('id', 'booking', 'space', 'user')
        }),
        ('Review Content', {
            'fields': ('rating', 'comment', 'full_comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    actions = ['filter_by_rating']
    
    def review_id_display(self, obj):
        return str(obj.id)[:8]
    review_id_display.short_description = 'Review ID'
    
    def space_display(self, obj):
        return obj.space.name
    space_display.short_description = 'Space'
    
    def user_display(self, obj):
        return obj.user.email
    user_display.short_description = 'User'
    
    def rating_display(self, obj):
        stars = '⭐' * obj.rating
        colors = {
            1: '#F44336',
            2: '#FF9800',
            3: '#FFC107',
            4: '#8BC34A',
            5: '#4CAF50'
        }
        color = colors.get(obj.rating, '#9E9E9E')
        return format_html(
            '<span style="color: {}; font-size: 1.2em;">{}</span> <strong>{}/5</strong>',
            color,
            stars,
            obj.rating
        )
    rating_display.short_description = 'Rating'
    
    def comment_preview(self, obj):
        preview = obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
        return preview
    comment_preview.short_description = 'Comment'
    
    def full_comment(self, obj):
        return obj.comment
    full_comment.short_description = 'Full Comment'
    
    def filter_by_rating(self, request, queryset):
        self.message_user(request, f'Viewing {queryset.count()} reviews.')
    filter_by_rating.short_description = 'View reviews by rating'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('booking', 'space', 'user')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['reservation_id_display', 'space_display', 'user_display', 'status', 'start', 'end', 'expires_at', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['space__name', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def reservation_id_display(self, obj):
        return str(obj.id)[:8]
    reservation_id_display.short_description = 'Reservation ID'

    def space_display(self, obj):
        return obj.space.name
    space_display.short_description = 'Space'

    def user_display(self, obj):
        return obj.user.email
    user_display.short_description = 'User'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('space', 'user')


@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = ['checkout_id_display', 'user_display', 'bookings_count', 'updated_at']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-updated_at']

    def checkout_id_display(self, obj):
        return str(obj.id)[:8]
    checkout_id_display.short_description = 'Checkout ID'

    def user_display(self, obj):
        return obj.user.email
    user_display.short_description = 'User'

    def bookings_count(self, obj):
        return obj.bookings.count()
    bookings_count.short_description = 'Bookings'
