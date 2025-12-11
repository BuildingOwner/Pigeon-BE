"""
Gmail API 클라이언트
"""
import base64
import time
from datetime import datetime, timedelta
from email.utils import parseaddr

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError


class GmailAPIClient:
    """Gmail API 래퍼 클래스"""

    BASE_URL = 'https://gmail.googleapis.com/gmail/v1/users/me'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'

    def __init__(self, user):
        """
        Args:
            user: User 모델 인스턴스 (gmail_access_token, gmail_refresh_token 필요)
        """
        self.user = user
        self._ensure_valid_token()

    def _ensure_valid_token(self):
        """토큰 유효성 확인 및 필요시 갱신"""
        if not self.user.gmail_access_token:
            raise ValidationError({
                'code': 'GMAIL_NOT_CONNECTED',
                'message': 'Gmail 계정이 연결되지 않았습니다.'
            })

        # 토큰 만료 확인 (5분 여유)
        if self.user.gmail_token_expires_at:
            if timezone.now() > self.user.gmail_token_expires_at - timedelta(minutes=5):
                self._refresh_token()

    def _refresh_token(self):
        """액세스 토큰 갱신"""
        if not self.user.gmail_refresh_token:
            raise ValidationError({
                'code': 'REFRESH_TOKEN_MISSING',
                'message': 'Refresh token이 없습니다. 다시 로그인해주세요.'
            })

        data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'refresh_token': self.user.gmail_refresh_token,
            'grant_type': 'refresh_token',
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()

            # 새 토큰 저장
            self.user.gmail_access_token = token_data['access_token']
            self.user.gmail_token_expires_at = timezone.now() + timedelta(
                seconds=token_data.get('expires_in', 3600)
            )
            self.user.save(update_fields=['_gmail_access_token', 'gmail_token_expires_at'])

        except requests.exceptions.RequestException as e:
            raise ValidationError({
                'code': 'TOKEN_REFRESH_FAILED',
                'message': f'토큰 갱신에 실패했습니다: {str(e)}'
            })

    def _get_headers(self):
        """API 요청 헤더"""
        return {
            'Authorization': f'Bearer {self.user.gmail_access_token}',
            'Content-Type': 'application/json',
        }

    def _request(self, method, endpoint, **kwargs):
        """API 요청 래퍼 (Rate limiting 처리)"""
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    timeout=30,
                    **kwargs
                )

                # Rate limit 처리 (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    raise ValidationError({
                        'code': 'RATE_LIMITED',
                        'message': 'Gmail API 요청 제한에 걸렸습니다. 잠시 후 다시 시도해주세요.'
                    })

                # 401 토큰 만료 처리
                if response.status_code == 401:
                    self._refresh_token()
                    headers = self._get_headers()
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise ValidationError({
                        'code': 'GMAIL_API_ERROR',
                        'message': f'Gmail API 요청 실패: {str(e)}'
                    })

    def get_attachment(self, message_id: str, attachment_id: str) -> dict:
        """
        첨부파일 데이터 조회

        Args:
            message_id: Gmail 메시지 ID
            attachment_id: 첨부파일 ID

        Returns:
            dict: {
                'data': base64 인코딩된 파일 데이터,
                'size': 파일 크기
            }
        """
        endpoint = f"/messages/{message_id}/attachments/{attachment_id}"
        response = self._request('GET', endpoint)
        return response.json()

    def get_attachment_data(self, message_id: str, attachment_id: str) -> bytes:
        """
        첨부파일 바이너리 데이터 조회

        Args:
            message_id: Gmail 메시지 ID
            attachment_id: 첨부파일 ID

        Returns:
            bytes: 파일 바이너리 데이터
        """
        attachment = self.get_attachment(message_id, attachment_id)
        # Gmail API는 URL-safe base64 인코딩 사용
        data = attachment.get('data', '')
        return base64.urlsafe_b64decode(data)

    def list_messages(self, query: str = None, max_results: int = 20,
                      page_token: str = None) -> dict:
        """
        메시지 목록 조회

        Args:
            query: Gmail 검색 쿼리 (예: "after:2024/06/01")
            max_results: 최대 결과 수
            page_token: 페이지네이션 토큰

        Returns:
            dict: {
                'messages': [{'id': str, 'threadId': str}, ...],
                'nextPageToken': str (optional),
                'resultSizeEstimate': int
            }
        """
        params = {'maxResults': max_results}
        if query:
            params['q'] = query
        if page_token:
            params['pageToken'] = page_token

        response = self._request('GET', '/messages', params=params)
        return response.json()

    def get_message(self, message_id: str, format: str = 'full') -> dict:
        """
        메시지 상세 조회

        Args:
            message_id: Gmail 메시지 ID
            format: 응답 형식 ('minimal', 'full', 'raw', 'metadata')

        Returns:
            dict: Gmail 메시지 데이터
        """
        params = {'format': format}
        response = self._request('GET', f'/messages/{message_id}', params=params)
        return response.json()

    def get_history(self, start_history_id: str, history_types: list = None) -> dict:
        """
        변경 이력 조회 (증분 동기화용)

        Args:
            start_history_id: 시작 이력 ID
            history_types: 조회할 이력 유형 ('messageAdded', 'messageDeleted', 등)

        Returns:
            dict: {
                'history': [...],
                'historyId': str,
                'nextPageToken': str (optional)
            }
        """
        params = {'startHistoryId': start_history_id}
        if history_types:
            params['historyTypes'] = history_types

        response = self._request('GET', '/history', params=params)
        return response.json()

    def get_profile(self) -> dict:
        """
        Gmail 프로필 조회 (historyId 포함)

        Returns:
            dict: {
                'emailAddress': str,
                'messagesTotal': int,
                'threadsTotal': int,
                'historyId': str
            }
        """
        response = self._request('GET', '/profile')
        return response.json()

    def parse_message(self, message: dict) -> dict:
        """
        Gmail 메시지를 파싱하여 Mail 모델에 저장할 형태로 변환

        Args:
            message: Gmail API의 messages.get 응답

        Returns:
            dict: 파싱된 메일 데이터
        """
        headers = {h['name'].lower(): h['value'] for h in message.get('payload', {}).get('headers', [])}

        # 발신자 파싱
        sender_raw = headers.get('from', '')
        sender_name, sender_email = parseaddr(sender_raw)
        sender = sender_raw if sender_raw else 'Unknown'

        # 수신자 파싱
        recipients = []
        for recipient_type in ['to', 'cc', 'bcc']:
            recipient_header = headers.get(recipient_type, '')
            if recipient_header:
                for addr in recipient_header.split(','):
                    name, email = parseaddr(addr.strip())
                    if email:
                        recipients.append({
                            'type': recipient_type,
                            'email': email,
                            'name': name or email
                        })

        # 본문 추출
        body_html, body_text = self._extract_body(message.get('payload', {}))

        # 첨부파일 메타데이터 추출
        attachments = self._extract_attachments(message.get('payload', {}))

        # 수신 시간 파싱 (internalDate는 밀리초 단위)
        internal_date = int(message.get('internalDate', 0))
        received_at = timezone.make_aware(
            datetime.fromtimestamp(internal_date / 1000),
            timezone.get_current_timezone()
        )

        return {
            'gmail_id': message.get('id'),
            'thread_id': message.get('threadId'),
            'subject': headers.get('subject', '(제목 없음)'),
            'sender': sender,
            'sender_email': sender_email or sender,
            'recipients': recipients,
            'snippet': message.get('snippet', ''),
            'body_html': body_html or body_text or '',
            'attachments': attachments,
            'has_attachments': len(attachments) > 0,
            'is_read': 'UNREAD' not in message.get('labelIds', []),
            'is_starred': 'STARRED' in message.get('labelIds', []),
            'received_at': received_at,
            'history_id': message.get('historyId'),
        }

    def _extract_body(self, payload: dict) -> tuple:
        """
        메일 본문 추출 (HTML 우선, 없으면 plain text)

        Args:
            payload: Gmail message payload

        Returns:
            tuple: (body_html, body_text)
        """
        body_html = ''
        body_text = ''

        def extract_from_part(part):
            nonlocal body_html, body_text
            mime_type = part.get('mimeType', '')
            body_data = part.get('body', {}).get('data', '')

            if body_data:
                decoded = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                if mime_type == 'text/html':
                    body_html = decoded
                elif mime_type == 'text/plain':
                    body_text = decoded

            # multipart 처리
            for sub_part in part.get('parts', []):
                extract_from_part(sub_part)

        extract_from_part(payload)
        return body_html, body_text

    def _extract_attachments(self, payload: dict) -> list:
        """
        첨부파일 메타데이터 추출

        Args:
            payload: Gmail message payload

        Returns:
            list: 첨부파일 목록
        """
        attachments = []

        def extract_from_part(part):
            filename = part.get('filename', '')
            attachment_id = part.get('body', {}).get('attachmentId')

            if filename and attachment_id:
                attachments.append({
                    'id': attachment_id,
                    'name': filename,
                    'size': part.get('body', {}).get('size', 0),
                    'mimeType': part.get('mimeType', 'application/octet-stream'),
                })

            for sub_part in part.get('parts', []):
                extract_from_part(sub_part)

        extract_from_part(payload)
        return attachments
