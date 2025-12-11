from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 Serializer"""

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'name',
            'picture',
            'is_initial_sync_done',
            'last_sync_at',
            'created_at',
        ]
        read_only_fields = ['id', 'email', 'created_at']


class TokenResponseSerializer(serializers.Serializer):
    """JWT 토큰 응답 Serializer"""
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    expires_in = serializers.IntegerField()
    user = UserSerializer()
