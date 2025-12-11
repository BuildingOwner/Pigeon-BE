from rest_framework import serializers

from apps.folders.serializers import FolderSerializer

from .models import Mail


class MailListSerializer(serializers.ModelSerializer):
    """메일 목록용 Serializer (간략)"""
    folder = FolderSerializer(read_only=True)

    class Meta:
        model = Mail
        fields = [
            'id',
            'gmail_id',
            'thread_id',
            'subject',
            'sender',
            'sender_email',
            'snippet',
            'folder',
            'has_attachments',
            'is_read',
            'is_starred',
            'is_classified',
            'received_at',
        ]


class MailDetailSerializer(serializers.ModelSerializer):
    """메일 상세용 Serializer (전체)"""
    folder = FolderSerializer(read_only=True)

    class Meta:
        model = Mail
        fields = [
            'id',
            'gmail_id',
            'thread_id',
            'subject',
            'sender',
            'sender_email',
            'recipients',
            'snippet',
            'body_html',
            'folder',
            'attachments',
            'has_attachments',
            'is_read',
            'is_starred',
            'is_classified',
            'received_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'gmail_id', 'created_at', 'updated_at']


class MailUpdateSerializer(serializers.ModelSerializer):
    """메일 상태 업데이트용 Serializer"""

    class Meta:
        model = Mail
        fields = ['is_read', 'is_starred']
