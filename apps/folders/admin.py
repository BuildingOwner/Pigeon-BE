from django.contrib import admin
from .models import Folder


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['path', 'user', 'depth', 'mail_count', 'unread_count', 'order']
    list_filter = ['depth', 'user']
    search_fields = ['name', 'path', 'user__email']
    ordering = ['user', 'order', 'name']

    fieldsets = (
        (None, {'fields': ('user', 'name', 'parent')}),
        ('트리 구조', {'fields': ('path', 'depth', 'order')}),
        ('통계', {'fields': ('mail_count', 'unread_count')}),
        ('타임스탬프', {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ['path', 'depth', 'created_at', 'updated_at']
