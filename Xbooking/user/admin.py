from django.contrib import admin
from .models import User, VerificationCode
from .forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
import secrets
import string
# Register your models here.


class VerificationCodeInline(admin.TabularInline):
    """Inline admin for verification codes"""
    model = VerificationCode
    extra = 0
    readonly_fields = ('code', 'created_at', 'is_used')
    fields = ('code', 'created_at', 'is_used')
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    """Admin interface for verification codes"""
    list_display = ['user_email', 'code', 'created_at', 'is_used', 'is_expired', 'code_age']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'user__full_name', 'code']
    readonly_fields = ['code', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def is_expired(self, obj):
        """Check if verification code is expired (15 minutes)"""
        expiry_time = obj.created_at + timedelta(minutes=15)
        is_expired = timezone.now() > expiry_time
        
        if is_expired:
            return format_html('<span style="color: red;">✗ Expired</span>')
        else:
            return format_html('<span style="color: green;">✓ Valid</span>')
    is_expired.short_description = 'Status'
    is_expired.allow_tags = True
    
    def code_age(self, obj):
        """Display how long ago the code was created"""
        now = timezone.now()
        age = now - obj.created_at
        
        if age.days > 0:
            return f"{age.days} days ago"
        elif age.seconds > 3600:
            hours = age.seconds // 3600
            return f"{hours} hours ago"
        else:
            minutes = age.seconds // 60
            return f"{minutes} minutes ago"
    code_age.short_description = 'Age'
    
    def clear_expired_codes(self, request, queryset):
        """Admin action to clear expired verification codes"""
        expired_time = timezone.now() - timedelta(minutes=15)
        expired_codes = queryset.filter(created_at__lt=expired_time)
        count = expired_codes.count()
        expired_codes.delete()
        
        self.message_user(
            request,
            f'Deleted {count} expired verification code(s).',
            messages.SUCCESS
        )
    clear_expired_codes.short_description = "Delete expired verification codes"
    
    def clear_used_codes(self, request, queryset):
        """Admin action to clear used verification codes"""
        used_codes = queryset.filter(is_used=True)
        count = used_codes.count()
        used_codes.delete()
        
        self.message_user(
            request,
            f'Deleted {count} used verification code(s).',
            messages.SUCCESS
        )
    clear_used_codes.short_description = "Delete used verification codes"
    
    actions = ['clear_expired_codes', 'clear_used_codes']



class UserAdmin(admin.ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    inlines = [VerificationCodeInline]
    
    list_display = ["id", "full_name", "email", "last_login", "is_active", "verification_code_status", "password_reset_button"]
    list_filter = ("is_active", "created_at")
    search_fields = ("full_name", "email", "id")
    ordering = ("full_name",)
    readonly_fields = ("id", "created_at", "last_login")
    
    fieldsets = (
        (None, {"fields": ("id", "full_name", "password")}),
        (_("Personal info"), {"fields": ("avatar_url", "email", "is_active")}),
        (_("Important dates"), {"fields": ("last_login", "created_at")}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('full_name', 'email', 'avatar_url', 'password1', 'password2'),
        }),
    )
    
    def verification_code_status(self, obj):
        """Display verification code status"""
        active_codes = VerificationCode.objects.filter(
            user=obj,
            is_used=False,
            created_at__gt=timezone.now() - timedelta(minutes=15)
        )
        
        if active_codes.exists():
            latest_code = active_codes.order_by('-created_at').first()
            expires_at = latest_code.created_at + timedelta(minutes=15)
            return format_html(
                '<span style="color: green;">✓ Active Code</span><br>'
                '<small>Code: {}<br>Expires: {}</small>',
                latest_code.code,
                expires_at.strftime("%H:%M")
            )
        
        expired_codes = VerificationCode.objects.filter(user=obj, is_used=False).count()
        used_codes = VerificationCode.objects.filter(user=obj, is_used=True).count()
        
        if expired_codes > 0 or used_codes > 0:
            return format_html(
                '<span style="color: orange;">Expired/Used</span><br>'
                '<small>{} expired, {} used</small>',
                expired_codes,
                used_codes
            )
        
        return format_html('<span style="color: gray;">No codes</span>')
    verification_code_status.short_description = "Verification Codes"
    verification_code_status.allow_tags = True
    
    def password_reset_button(self, obj):
        """Add action buttons in the admin list view"""
        if obj.pk:
            buttons = []
            
            # Password reset button
            buttons.append(format_html(
                '<a class="button" href="{}" onclick="return confirm(\'Are you sure you want to reset this user\\\'s password?\')">Reset Password</a>',
                reverse('admin:reset_user_password', args=[obj.pk])
            ))
            
            # Clear verification codes button
            verification_codes = VerificationCode.objects.filter(user=obj)
            if verification_codes.exists():
                buttons.append(format_html(
                    '<a class="button" href="{}" onclick="return confirm(\'Are you sure you want to clear all verification codes?\')">Clear Codes</a>',
                    reverse('admin:clear_verification_codes', args=[obj.pk])
                ))
            
            return format_html('<br>'.join(buttons))
        return "-"
    password_reset_button.short_description = "Actions"
    password_reset_button.allow_tags = True
    
    def get_urls(self):
        """Add custom URLs for admin actions"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:user_id>/reset-password-custom/',
                self.admin_site.admin_view(self.reset_user_password),
                name='reset_user_password',
            ),
            path(
                '<uuid:user_id>/clear-verification-codes/',
                self.admin_site.admin_view(self.clear_verification_codes),
                name='clear_verification_codes',
            ),
        ]
        return custom_urls + urls
    
    def reset_user_password(self, request, user_id):
        """Reset user password and display the new password"""
        user = get_object_or_404(User, pk=user_id)
        
        # Generate a secure random password
        new_password = self.generate_secure_password()
        
        # Set the new password (this will automatically hash it)
        user.set_password(new_password)
        user.save()
        
        # Clear any existing verification codes
        VerificationCode.objects.filter(user=user).delete()
        
        # Add success message with the new password
        messages.success(
            request,
            format_html(
                'Password for user "<strong>{}</strong>" has been reset successfully.<br>'
                'New password: <strong>{}</strong><br>'
                '<em>Please share this securely with the user and ask them to change it on first login.</em><br>'
                'All verification codes have been cleared.',
                user.full_name,
                new_password
            )
        )
        
        # Redirect back to the user list
        return HttpResponseRedirect(reverse('admin:user_user_changelist'))
    
    def clear_verification_codes(self, request, user_id):
        """Clear all verification codes for a user"""
        user = get_object_or_404(User, pk=user_id)
        count = VerificationCode.objects.filter(user=user).count()
        VerificationCode.objects.filter(user=user).delete()
        
        messages.success(
            request,
            f'Cleared {count} verification code(s) for user "{user.full_name}".'
        )
        
        return HttpResponseRedirect(reverse('admin:user_user_changelist'))
    
    def clear_expired_verification_codes(self, request, queryset):
        """Admin action to clear expired verification codes for selected users"""
        expired_time = timezone.now() - timedelta(minutes=15)
        total_cleared = 0
        
        for user in queryset:
            expired_codes = VerificationCode.objects.filter(
                user=user,
                created_at__lt=expired_time
            )
            count = expired_codes.count()
            expired_codes.delete()
            total_cleared += count
        
        if total_cleared:
            self.message_user(
                request,
                f'Cleared {total_cleared} expired verification code(s) for {queryset.count()} user(s).',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'No expired verification codes found for selected users.',
                messages.INFO
            )
    
    clear_expired_verification_codes.short_description = "Clear expired verification codes"
    
    def clear_all_verification_codes(self, request, queryset):
        """Admin action to clear all verification codes for selected users"""
        total_cleared = 0
        
        for user in queryset:
            count = VerificationCode.objects.filter(user=user).count()
            VerificationCode.objects.filter(user=user).delete()
            total_cleared += count
        
        self.message_user(
            request,
            f'Cleared {total_cleared} verification code(s) for {queryset.count()} user(s).',
            messages.SUCCESS
        )
    
    clear_all_verification_codes.short_description = "Clear all verification codes"
    
    actions = ['clear_expired_verification_codes', 'clear_all_verification_codes']
    
    def generate_secure_password(self, length=12):
        """Generate a secure random password"""
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special_chars = "!@#$%^&*"
        
        # Ensure password has at least one character from each set
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special_chars)
        ]
        
        # Fill the rest with random characters from all sets
        all_chars = lowercase + uppercase + digits + special_chars
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password list to randomize positions
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def get_form(self, request, obj=None, **kwargs):
        """Use special form during user creation"""
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)
    
    def save_model(self, request, obj, form, change):
        """Override save to ensure password is hashed when changed manually"""
        if not change:
            # New user creation is handled by the form
            super().save_model(request, obj, form, change)
        else:
            # For existing users, check if password field was manually edited
            if hasattr(form, 'cleaned_data') and 'password' in form.changed_data:
                # Only hash if it's not already hashed and looks like a plain text password
                password = form.cleaned_data.get('password', '')
                if password and not password.startswith('pbkdf2_sha256$'):
                    obj.set_password(password)
            super().save_model(request, obj, form, change)

admin.site.register(User, UserAdmin)
