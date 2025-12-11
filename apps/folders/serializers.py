from rest_framework import serializers
from .models import Folder


class FolderSerializer(serializers.ModelSerializer):
    """폴더 Serializer"""

    class Meta:
        model = Folder
        fields = [
            'id',
            'name',
            'path',
            'depth',
            'parent_id',
            'mail_count',
            'unread_count',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'path', 'depth', 'created_at', 'updated_at']


class FolderTreeSerializer(serializers.ModelSerializer):
    """폴더 트리 Serializer (재귀)"""
    children = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            'id',
            'name',
            'path',
            'depth',
            'mail_count',
            'unread_count',
            'order',
            'children',
        ]

    def get_children(self, obj):
        if hasattr(obj, 'children_list'):
            return FolderTreeSerializer(obj.children_list, many=True).data
        return []
