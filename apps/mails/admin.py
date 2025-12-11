from django.contrib import admin

from .models import Mail


@admin.register(Mail)
class MailAdmin(admin.ModelAdmin):
    list_display = ['subject', 'sender_email', 'folder', 'is_read', 'is_classified', 'received_at']
    list_filter = ['is_read', 'is_classified', 'is_starred', 'is_deleted', 'has_attachments']
    search_fields = ['subject', 'sender', 'sender_email', 'snippet']
    ordering = ['-received_at']

    fieldsets = (
        ('기본 정보', {'fields': ('user', 'folder', 'gmail_id', 'thread_id')}),
        ('메일 내용', {'fields': ('subject', 'sender', 'sender_email', 'recipients', 'snippet', 'body_html')}),
        ('첨부파일', {'fields': ('has_attachments', 'attachments')}),
        ('상태', {'fields': ('is_read', 'is_starred', 'is_classified', 'is_deleted')}),
        ('시간', {'fields': ('received_at', 'created_at', 'updated_at')}),
    )

    readonly_fields = ['created_at', 'updated_at']
