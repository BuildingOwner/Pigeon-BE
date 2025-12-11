"""
Gmail 동기화 서비스
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.mails.models import Mail
from apps.mails.services import GmailAPIClient

logger = logging.getLogger(__name__)


class SyncState:
    """동기화 상태 관리 (메모리 기반)"""
    _instances = {}

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.sync_id = f"sync_{uuid.uuid4().hex[:8]}"
        self.state = 'idle'  # idle, in_progress, completed, failed
        self.sync_type = 'initial'  # initial, incremental
        self.total = 0
        self.synced = 0
        self.classified = 0
        self.started_at = None
        self.completed_at = None
        self.error = None
        self.should_stop = False

    @classmethod
    def get_or_create(cls, user_id: int) -> 'SyncState':
        if user_id not in cls._instances:
            cls._instances[user_id] = cls(user_id)
        return cls._instances[user_id]

    @classmethod
    def get(cls, user_id: int) -> Optional['SyncState']:
        return cls._instances.get(user_id)

    def reset(self, sync_type: str = 'initial'):
        self.sync_id = f"sync_{uuid.uuid4().hex[:8]}"
        self.state = 'in_progress'
        self.sync_type = sync_type
        self.total = 0
        self.synced = 0
        self.classified = 0
        self.started_at = timezone.now()
        self.completed_at = None
        self.error = None
        self.should_stop = False

    def to_dict(self) -> dict:
        return {
            'sync_id': self.sync_id,
            'state': self.state,
            'type': self.sync_type,
            'progress': {
                'total': self.total,
                'synced': self.synced,
                'classified': self.classified,
                'percentage': int((self.synced / self.total * 100) if self.total > 0 else 0),
            },
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
        }


class GmailSyncService:
    """Gmail 동기화 서비스"""

    BATCH_SIZE = 20  # 배치 크기
    INITIAL_SYNC_MONTHS = 6  # 초기 동기화 기간 (개월)

    def __init__(self, user):
        self.user = user
        self.gmail_client = GmailAPIClient(user)
        self.sync_state = SyncState.get_or_create(user.id)

    def start_sync(self, full_sync: bool = False) -> dict:
        """
        동기화 시작

        Args:
            full_sync: True이면 전체 재동기화

        Returns:
            dict: 동기화 시작 정보
        """
        # 이미 동기화 중인지 확인
        if self.sync_state.state == 'in_progress':
            return {
                'status': 'already_running',
                'sync_id': self.sync_state.sync_id,
            }

        # 동기화 타입 결정
        if full_sync or not self.user.is_initial_sync_done:
            sync_type = 'initial'
        else:
            sync_type = 'incremental'

        # 상태 초기화
        self.sync_state.reset(sync_type)

        # 동기화 실행
        try:
            if sync_type == 'initial':
                self._run_initial_sync()
            else:
                self._run_incremental_sync()
        except Exception as e:
            logger.exception(f"Sync failed for user {self.user.id}")
            self.sync_state.state = 'failed'
            self.sync_state.error = str(e)
            raise

        return {
            'sync_id': self.sync_state.sync_id,
            'type': sync_type,
            'started_at': self.sync_state.started_at.isoformat(),
        }

    def get_status(self) -> dict:
        """동기화 상태 조회"""
        return self.sync_state.to_dict()

    def stop_sync(self) -> dict:
        """동기화 중단"""
        if self.sync_state.state != 'in_progress':
            return {
                'status': 'not_running',
                'message': '실행 중인 동기화가 없습니다.',
            }

        self.sync_state.should_stop = True
        self.sync_state.state = 'completed'
        self.sync_state.completed_at = timezone.now()

        return {
            'sync_id': self.sync_state.sync_id,
            'synced_count': self.sync_state.synced,
        }

    def _run_initial_sync(self):
        """초기 동기화 실행 (최근 6개월)"""
        # 6개월 전 날짜 계산
        after_date = (datetime.now() - timedelta(days=self.INITIAL_SYNC_MONTHS * 30)).strftime('%Y/%m/%d')
        query = f'after:{after_date}'

        logger.info(f"Starting initial sync for user {self.user.id} with query: {query}")

        # 메일 목록 조회
        page_token = None
        all_message_ids = []

        while True:
            if self.sync_state.should_stop:
                break

            result = self.gmail_client.list_messages(
                query=query,
                max_results=100,
                page_token=page_token
            )

            messages = result.get('messages', [])
            all_message_ids.extend([m['id'] for m in messages])

            page_token = result.get('nextPageToken')
            if not page_token:
                break

        self.sync_state.total = len(all_message_ids)
        logger.info(f"Found {self.sync_state.total} messages to sync")

        # 이미 동기화된 메일 제외
        existing_gmail_ids = set(
            Mail.objects.filter(
                user=self.user,
                gmail_id__in=all_message_ids
            ).values_list('gmail_id', flat=True)
        )

        new_message_ids = [mid for mid in all_message_ids if mid not in existing_gmail_ids]
        self.sync_state.total = len(new_message_ids)

        # 배치 단위로 메일 상세 조회 및 저장
        for i in range(0, len(new_message_ids), self.BATCH_SIZE):
            if self.sync_state.should_stop:
                break

            batch_ids = new_message_ids[i:i + self.BATCH_SIZE]
            self._sync_batch(batch_ids)

        # 완료 처리
        if not self.sync_state.should_stop:
            self.sync_state.state = 'completed'
            self.sync_state.completed_at = timezone.now()

            # 사용자 상태 업데이트
            profile = self.gmail_client.get_profile()
            self.user.gmail_history_id = profile.get('historyId', '')
            self.user.is_initial_sync_done = True
            self.user.last_sync_at = timezone.now()
            self.user.save(update_fields=['gmail_history_id', 'is_initial_sync_done', 'last_sync_at'])

            logger.info(f"Initial sync completed for user {self.user.id}: {self.sync_state.synced} messages synced")

    def _run_incremental_sync(self):
        """증분 동기화 실행 (History API 사용)"""
        if not self.user.gmail_history_id:
            # history_id가 없으면 초기 동기화 필요
            logger.warning(f"No history_id for user {self.user.id}, running initial sync")
            self._run_initial_sync()
            return

        logger.info(f"Starting incremental sync for user {self.user.id} from history_id: {self.user.gmail_history_id}")

        try:
            result = self.gmail_client.get_history(
                start_history_id=self.user.gmail_history_id,
                history_types=['messageAdded']
            )

            history_list = result.get('history', [])
            new_history_id = result.get('historyId')

            # 새 메시지 ID 수집
            new_message_ids = set()
            for history in history_list:
                for message_added in history.get('messagesAdded', []):
                    message = message_added.get('message', {})
                    # INBOX 라벨이 있는 메시지만 동기화
                    if 'INBOX' in message.get('labelIds', []):
                        new_message_ids.add(message.get('id'))

            # 이미 동기화된 메일 제외
            existing_gmail_ids = set(
                Mail.objects.filter(
                    user=self.user,
                    gmail_id__in=list(new_message_ids)
                ).values_list('gmail_id', flat=True)
            )

            new_message_ids = new_message_ids - existing_gmail_ids
            self.sync_state.total = len(new_message_ids)

            logger.info(f"Found {len(new_message_ids)} new messages")

            # 메일 동기화
            if new_message_ids:
                self._sync_batch(list(new_message_ids))

            # 완료 처리
            self.sync_state.state = 'completed'
            self.sync_state.completed_at = timezone.now()

            # history_id 업데이트
            if new_history_id:
                self.user.gmail_history_id = new_history_id
            self.user.last_sync_at = timezone.now()
            self.user.save(update_fields=['gmail_history_id', 'last_sync_at'])

            logger.info(f"Incremental sync completed for user {self.user.id}: {self.sync_state.synced} messages synced")

        except Exception as e:
            # history_id가 유효하지 않은 경우 (404 등) 초기 동기화 필요할 수 있음
            if '404' in str(e) or 'notFound' in str(e):
                logger.warning(f"History not found for user {self.user.id}, need to resync")
                # 현재 프로필에서 새 history_id 가져오기
                profile = self.gmail_client.get_profile()
                self.user.gmail_history_id = profile.get('historyId', '')
                self.user.save(update_fields=['gmail_history_id'])
            raise

    @transaction.atomic
    def _sync_batch(self, message_ids: list):
        """배치 단위로 메일 동기화"""
        for message_id in message_ids:
            if self.sync_state.should_stop:
                break

            try:
                # 메일 상세 조회
                raw_message = self.gmail_client.get_message(message_id, format='full')
                parsed = self.gmail_client.parse_message(raw_message)

                # DB 저장
                Mail.objects.update_or_create(
                    user=self.user,
                    gmail_id=parsed['gmail_id'],
                    defaults={
                        'thread_id': parsed['thread_id'],
                        'subject': parsed['subject'][:500],  # 최대 길이 제한
                        'sender': parsed['sender'][:200],
                        'sender_email': parsed['sender_email'][:254],
                        'recipients': parsed['recipients'],
                        'snippet': parsed['snippet'],
                        'body_html': parsed['body_html'],
                        'attachments': parsed['attachments'],
                        'has_attachments': parsed['has_attachments'],
                        'is_read': parsed['is_read'],
                        'is_starred': parsed['is_starred'],
                        'received_at': parsed['received_at'],
                        'is_classified': False,
                    }
                )

                self.sync_state.synced += 1
                logger.debug(f"Synced message {message_id}")

            except Exception as e:
                logger.error(f"Failed to sync message {message_id}: {e}")
                continue
