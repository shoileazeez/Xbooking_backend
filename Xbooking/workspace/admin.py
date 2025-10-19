from django.contrib import admin
from workspace.models import Workspace, Branch, WorkspaceUser, Space
from django.utils.html import format_html


class BranchInline(admin.TabularInline):
    """Inline admin for branches"""
    model = Branch
    extra = 0
    fields = ('name', 'city', 'email', 'is_active')
    readonly_fields = ('id', 'created_at')


class WorkspaceUserInline(admin.TabularInline):
    """Inline admin for workspace members"""
    model = WorkspaceUser
    extra = 0
    fields = ('user', 'role', 'is_active', 'joined_at')
    readonly_fields = ('joined_at',)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    """Admin interface for Workspace"""
    list_display = ['name', 'admin', 'email', 'is_active', 'branches_count', 'members_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'admin__full_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [BranchInline, WorkspaceUserInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'admin', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('Media', {
            'fields': ('logo_url',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def branches_count(self, obj):
        """Display number of branches"""
        count = obj.branches.count()
        return format_html(
            '<span style="background-color: #417505; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    branches_count.short_description = 'Branches'

    def members_count(self, obj):
        """Display number of members"""
        count = obj.members.count()
        return format_html(
            '<span style="background-color: #417505; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    members_count.short_description = 'Members'


class SpaceInline(admin.TabularInline):
    """Inline admin for spaces"""
    model = Space
    extra = 0
    fields = ('name', 'space_type', 'capacity', 'hourly_rate', 'is_available')
    readonly_rules = ('id', 'created_at')


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    """Admin interface for Branch"""
    list_display = ['name', 'workspace', 'city', 'manager', 'is_active', 'spaces_count', 'created_at']
    list_filter = ['is_active', 'workspace', 'created_at']
    search_fields = ['name', 'email', 'city', 'manager__full_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [SpaceInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'workspace', 'name', 'description', 'manager', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code', 'latitude', 'longitude')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def spaces_count(self, obj):
        """Display number of spaces"""
        count = obj.spaces.count()
        return format_html(
            '<span style="background-color: #417505; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    spaces_count.short_description = 'Spaces'


@admin.register(WorkspaceUser)
class WorkspaceUserAdmin(admin.ModelAdmin):
    """Admin interface for WorkspaceUser"""
    list_display = ['user_name', 'workspace', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active', 'workspace', 'joined_at']
    search_fields = ['user__full_name', 'user__email', 'workspace__name']
    readonly_fields = ['id', 'joined_at', 'updated_at']
    
    fieldsets = (
        ('Member Information', {
            'fields': ('id', 'user', 'workspace', 'role', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_name(self, obj):
        """Display user name"""
        return obj.user.full_name
    user_name.short_description = 'User'
    user_name.admin_order_field = 'user__full_name'


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    """Admin interface for Space"""
    list_display = ['name', 'branch', 'space_type', 'capacity', 'hourly_rate', 'is_available', 'created_at']
    list_filter = ['space_type', 'is_available', 'branch__workspace', 'created_at']
    search_fields = ['name', 'branch__name', 'branch__workspace__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'branch', 'name', 'description', 'space_type', 'is_available')
        }),
        ('Capacity & Pricing', {
            'fields': ('capacity', 'hourly_rate', 'daily_rate', 'monthly_rate')
        }),
        ('Media & Amenities', {
            'fields': ('image_url', 'amenities')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
