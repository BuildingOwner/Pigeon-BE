"""
커스텀 권한 클래스
"""
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    객체 소유자만 접근 가능
    """
    def has_object_permission(self, request, view, obj):
        # 객체의 user 필드가 요청 사용자와 일치하는지 확인
        return obj.user == request.user
