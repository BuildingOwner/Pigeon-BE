"""
Google OAuth2 인증 서비스
"""
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError


class GoogleOAuthService:
    """Google OAuth2 인증 서비스"""

    # Google OAuth2 엔드포인트
    AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify',
        ]

        # 환경변수 검증
        if not self.client_id or not self.client_secret:
            raise ValidationError({
                'error': 'Google OAuth credentials not configured',
                'message': 'GOOGLE_CLIENT_ID 및 GOOGLE_CLIENT_SECRET 환경변수를 설정해주세요.'
            })

    def generate_state(self) -> str:
        """CSRF 방지를 위한 state 값 생성"""
        return secrets.token_urlsafe(32)

    def get_authorization_url(self, state: str) -> str:
        """
        OAuth 인증 URL 생성

        Args:
            state: CSRF 방지를 위한 state 값

        Returns:
            Google OAuth2 인증 페이지 URL
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'access_type': 'offline',  # refresh_token을 받기 위해 필요
            'prompt': 'consent',  # 항상 consent 화면 표시 (refresh_token 보장)
            'state': state,
        }

        return f"{self.AUTHORIZATION_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        """
        인증 코드를 액세스 토큰으로 교환

        Args:
            code: Google에서 받은 인증 코드

        Returns:
            dict: {
                'access_token': str,
                'refresh_token': str,
                'expires_in': int,
                'token_type': str,
            }

        Raises:
            ValidationError: 토큰 교환 실패 시
        """
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()

            # refresh_token이 없는 경우 경고
            if 'refresh_token' not in token_data:
                # 이미 인증된 사용자의 경우 refresh_token이 없을 수 있음
                # prompt=consent를 사용하면 항상 받을 수 있지만, 없는 경우도 처리
                token_data['refresh_token'] = None

            return token_data

        except requests.exceptions.RequestException as e:
            raise ValidationError({
                'error': 'token_exchange_failed',
                'message': f'Google 토큰 교환에 실패했습니다: {str(e)}'
            })

    def get_user_info(self, access_token: str) -> dict:
        """
        액세스 토큰으로 사용자 정보 조회

        Args:
            access_token: Google 액세스 토큰

        Returns:
            dict: {
                'id': str,
                'email': str,
                'verified_email': bool,
                'name': str,
                'given_name': str,
                'family_name': str,
                'picture': str,
            }

        Raises:
            ValidationError: 사용자 정보 조회 실패 시
        """
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        try:
            response = requests.get(self.USERINFO_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise ValidationError({
                'error': 'userinfo_fetch_failed',
                'message': f'Google 사용자 정보 조회에 실패했습니다: {str(e)}'
            })

    def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh 토큰으로 새로운 액세스 토큰 발급

        Args:
            refresh_token: Google Refresh Token

        Returns:
            dict: {
                'access_token': str,
                'expires_in': int,
                'token_type': str,
            }

        Raises:
            ValidationError: 토큰 갱신 실패 시
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise ValidationError({
                'error': 'token_refresh_failed',
                'message': f'Google 토큰 갱신에 실패했습니다: {str(e)}'
            })
