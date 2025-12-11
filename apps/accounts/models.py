from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet


class User(AbstractUser):
    """Gmail OAuth2 인증 사용자"""

    # Gmail 관련 (암호화 저장)
    email = models.EmailField(unique=True)
    _gmail_access_token = models.TextField(db_column='gmail_access_token', blank=True)
    _gmail_refresh_token = models.TextField(db_column='gmail_refresh_token', blank=True)
    gmail_token_expires_at = models.DateTimeField(null=True, blank=True)
    gmail_history_id = models.CharField(max_length=50, blank=True)  # 증분 동기화용

    # 프로필
    name = models.CharField(max_length=100, blank=True)
    picture = models.URLField(blank=True)

    # 동기화 상태
    last_sync_at = models.DateTimeField(null=True, blank=True)
    is_initial_sync_done = models.BooleanField(default=False)

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'

    def __str__(self):
        return self.email

    # ===== 토큰 암호화/복호화 =====
    @staticmethod
    def _get_fernet():
        """Fernet 암호화 객체 반환"""
        key = settings.TOKEN_ENCRYPTION_KEY.encode()
        return Fernet(key)

    @property
    def gmail_access_token(self):
        """Access Token 복호화"""
        if not self._gmail_access_token:
            return ''
        try:
            return self._get_fernet().decrypt(
                self._gmail_access_token.encode()
            ).decode()
        except Exception:
            return ''

    @gmail_access_token.setter
    def gmail_access_token(self, value):
        """Access Token 암호화 저장"""
        if value:
            self._gmail_access_token = self._get_fernet().encrypt(
                value.encode()
            ).decode()
        else:
            self._gmail_access_token = ''

    @property
    def gmail_refresh_token(self):
        """Refresh Token 복호화"""
        if not self._gmail_refresh_token:
            return ''
        try:
            return self._get_fernet().decrypt(
                self._gmail_refresh_token.encode()
            ).decode()
        except Exception:
            return ''

    @gmail_refresh_token.setter
    def gmail_refresh_token(self, value):
        """Refresh Token 암호화 저장"""
        if value:
            self._gmail_refresh_token = self._get_fernet().encrypt(
                value.encode()
            ).decode()
        else:
            self._gmail_refresh_token = ''
