"""
Sync Serializers
"""
from rest_framework import serializers


class SyncStartSerializer(serializers.Serializer):
    """동기화 시작 요청 Serializer"""
    full_sync = serializers.BooleanField(default=False, required=False)


class SyncProgressSerializer(serializers.Serializer):
    """동기화 진행률 Serializer"""
    total = serializers.IntegerField()
    synced = serializers.IntegerField()
    classified = serializers.IntegerField()
    percentage = serializers.IntegerField()


class SyncStatusSerializer(serializers.Serializer):
    """동기화 상태 Serializer"""
    sync_id = serializers.CharField()
    state = serializers.ChoiceField(choices=['idle', 'in_progress', 'completed', 'failed'])
    type = serializers.ChoiceField(choices=['initial', 'incremental'])
    progress = SyncProgressSerializer()
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    error = serializers.CharField(allow_null=True)
