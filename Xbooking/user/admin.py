from django.contrib import admin
from .models import User
from .forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404
import secrets
import string
# Register your models here.



class UserAdmin(admin.ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    
    list_display = ["id", "full_name", "email", "last_login", "is_active", "password_reset_button"]
    list_filter = ("is_active", "date_joined")
    search_fields = ("full_name", "email", "id")
    ordering = ("full_name",)
    readonly_fields = ("id", "date_joined", "last_login")
    
    fieldsets = (
        (None, {"fields": ("id", "full_name", "password")}),
        (_("Personal info"), {"fields": ("avatar_url", "email", "is_active")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('full_name', 'email', 'avatar_url', 'password1', 'password2'),
        }),
    )
    
    def password_reset_button(self, obj):
        """Add a password reset button in the admin list view"""
        if obj.pk:
            return format_html(
                '<a class="button" href="{}" onclick="return confirm(\'Are you sure you want to reset this user\\\'s password?\')">Reset Password</a>',
                reverse('admin:reset_user_password', args=[obj.pk])
            )
        return "-"
    password_reset_button.short_description = "Password Reset"
    password_reset_button.allow_tags = True
    
    def get_urls(self):
        """Add custom URL for password reset"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:user_id>/reset-password-custom/',
                self.admin_site.admin_view(self.reset_user_password),
                name='reset_user_password',
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
        
        # Add success message with the new password
        messages.success(
            request,
            format_html(
                'Password for user "<strong>{}</strong>" has been reset successfully.<br>'
                'New password: <strong>{}</strong><br>'
                '<em>Please share this securely with the user and ask them to change it on first login.</em>',
                user.full_name,
                new_password
            )
        )
        
        # Redirect back to the user list
        return HttpResponseRedirect(reverse('admin:user_user_changelist'))
    
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
