"""
메일 분류 서비스
"""
import logging
import threading
import time
import uuid
from typing import Optional

from django.db import connection, transaction
from django.utils import timezone

from apps.folders.models import Folder
from apps.mails.models import Mail

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class ClassificationState:
    """분류 상태 관리 (메모리 기반)"""
    _instances = {}

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.classification_id = f"cls_{uuid.uuid4().hex[:8]}"
        self.state = 'pending'  # pending, in_progress, completed, failed
        self.total = 0
        self.processed = 0
        self.success = 0
        self.failed = 0
        self.new_folders_created = 0
        self.results = []  # 개별 결과
        self.started_at = None
        self.completed_at = None
        self.error = None
        self.provider = None  # 사용된 LLM 프로바이더 (gemini, openai)

    @classmethod
    def create(cls, user_id: int) -> 'ClassificationState':
        state = cls(user_id)
        cls._instances[state.classification_id] = state
        return state

    @classmethod
    def get(cls, classification_id: str) -> Optional['ClassificationState']:
        return cls._instances.get(classification_id)

    @classmethod
    def get_by_user(cls, user_id: int) -> Optional['ClassificationState']:
        for state in cls._instances.values():
            if state.user_id == user_id and state.state == 'in_progress':
                return state
        return None

    def start(self, total: int):
        self.state = 'in_progress'
        self.total = total
        self.started_at = timezone.now()

    def add_result(self, mail_id: int, status: str, folder_data: dict = None, error: str = None):
        self.processed += 1
        result = {
            'mail_id': mail_id,
            'status': status,
        }
        if status == 'success' and folder_data:
            self.success += 1
            result['folder'] = folder_data
            result['is_new_folder'] = folder_data.get('is_new_folder', False)
            result['confidence'] = folder_data.get('confidence', 0.0)
            if result['is_new_folder']:
                self.new_folders_created += 1
        else:
            self.failed += 1
            result['error'] = error or 'Unknown error'
            result['folder'] = None

        self.results.append(result)

    def complete(self):
        self.state = 'completed'
        self.completed_at = timezone.now()

    def fail(self, error: str):
        self.state = 'failed'
        self.error = error
        self.completed_at = timezone.now()

    def cancel(self):
        """분류 작업 취소"""
        self.state = 'cancelled'
        self.completed_at = timezone.now()

    def is_cancelled(self) -> bool:
        """취소 여부 확인"""
        return self.state == 'cancelled'

    def to_dict(self) -> dict:
        return {
            'classification_id': self.classification_id,
            'state': self.state,
            'provider': self.provider,
            'results': self.results,
            'summary': {
                'total': self.total,
                'success': self.success,
                'failed': self.failed,
                'new_folders_created': self.new_folders_created,
            },
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
        }


class ClassifierService:
    """메일 분류 서비스"""

    MAX_BATCH_SIZE = 20

    def __init__(self, user):
        self.user = user
        self.llm_client = LLMClient()

    def classify_mails(self, mail_ids: list) -> dict:
        """
        지정된 메일 분류 (백그라운드에서 실행)

        Args:
            mail_ids: 분류할 메일 ID 목록

        Returns:
            dict: 분류 시작 정보
        """
        mails = Mail.objects.filter(
            user=self.user,
            id__in=mail_ids,
            is_deleted=False
        )

        if not mails.exists():
            return {
                'status': 'no_mails',
                'message': '분류할 메일이 없습니다.',
            }

        state = ClassificationState.create(self.user.id)
        mail_ids_list = list(mails.values_list('id', flat=True))
        state.start(len(mail_ids_list))

        # 백그라운드 스레드에서 분류 실행
        user_id = self.user.id
        thread = threading.Thread(
            target=self._run_classification_in_background,
            args=(user_id, mail_ids_list, state.classification_id),
            daemon=True
        )
        thread.start()

        return {
            'classification_id': state.classification_id,
            'mail_count': state.total,
            'started_at': state.started_at.isoformat(),
        }

    def classify_unclassified(self) -> dict:
        """미분류 메일 일괄 분류 (백그라운드에서 실행)"""
        mails = Mail.objects.filter(
            user=self.user,
            is_classified=False,
            is_deleted=False
        )[:self.MAX_BATCH_SIZE]

        if not mails.exists():
            return {
                'status': 'no_mails',
                'message': '분류할 미분류 메일이 없습니다.',
            }

        state = ClassificationState.create(self.user.id)
        mail_ids_list = list(mails.values_list('id', flat=True))
        state.start(len(mail_ids_list))

        # 백그라운드 스레드에서 분류 실행
        user_id = self.user.id
        thread = threading.Thread(
            target=self._run_classification_in_background,
            args=(user_id, mail_ids_list, state.classification_id),
            daemon=True
        )
        thread.start()

        return {
            'classification_id': state.classification_id,
            'mail_count': state.total,
            'started_at': state.started_at.isoformat(),
        }

    def _run_classification_in_background(self, user_id: int, mail_ids: list, classification_id: str):
        """백그라운드에서 분류 실행"""
        try:
            # 스레드에서 새로운 DB 연결 사용
            connection.close()

            # User와 Mail 객체를 다시 가져옴 (스레드 안전)
            from apps.accounts.models import User
            self.user = User.objects.get(id=user_id)

            # 스레드에서 LLM 클라이언트 재생성
            self.llm_client = LLMClient()

            mails = Mail.objects.filter(
                user=self.user,
                id__in=mail_ids,
                is_deleted=False
            )
            mail_list = list(mails)

            state = ClassificationState.get(classification_id)
            if not state:
                logger.error(f"Classification state not found: {classification_id}")
                return

            # 사용 중인 LLM provider 설정
            state.provider = self.llm_client.provider

            self._process_classification(mail_list, state)
        except Exception as e:
            logger.exception(f"Classification failed for user {user_id}")
            state = ClassificationState.get(classification_id)
            if state:
                state.fail(str(e))
        finally:
            connection.close()

    def get_classification_status(self, classification_id: str) -> dict:
        """분류 상태 조회"""
        state = ClassificationState.get(classification_id)
        if not state:
            return None
        return state.to_dict()

    def _process_classification(self, mails: list, state: ClassificationState):
        """분류 처리"""
        existing_folders = list(
            Folder.objects.filter(user=self.user)
            .values('id', 'path', 'name', 'depth')
        )

        # 배치 분류 시도 (20개씩, 배치 간 딜레이)
        batch_size = 20
        for i in range(0, len(mails), batch_size):
            # 취소 확인
            if state.is_cancelled():
                logger.info(f"Classification cancelled for user {self.user.id}")
                return

            batch = mails[i:i + batch_size]
            self._classify_batch(batch, existing_folders, state)

            # 취소 확인 (배치 후)
            if state.is_cancelled():
                logger.info(f"Classification cancelled for user {self.user.id}")
                return

            # 다음 배치 전 대기 (rate limit 방지)
            if i + batch_size < len(mails):
                time.sleep(3)

        state.complete()
        logger.info(
            f"Classification completed for user {self.user.id}: "
            f"{state.success}/{state.total} success, {state.new_folders_created} new folders"
        )

    def _classify_batch(self, mails: list, existing_folders: list, state: ClassificationState):
        """배치 분류 처리"""
        mails_data = [
            {
                'id': mail.id,
                'subject': mail.subject,
                'sender': mail.sender,
                'snippet': mail.snippet
            }
            for mail in mails
        ]

        try:
            results = self.llm_client.classify_mails_batch(mails_data, existing_folders)
            # 실제 사용된 provider 업데이트 (fallback 전환 시 반영)
            state.provider = self.llm_client.provider
            mail_map = {mail.id: mail for mail in mails}

            for result in results:
                mail_id = result.get('mail_id')
                mail = mail_map.get(mail_id)
                if not mail:
                    continue

                try:
                    folder_data = self._apply_classification(mail, result, existing_folders)
                    state.add_result(mail_id, 'success', folder_data)
                except Exception as e:
                    logger.error(f"Failed to apply classification for mail {mail_id}: {e}")
                    state.add_result(mail_id, 'failed', error=str(e))

        except Exception as e:
            logger.error(f"Batch classification failed: {e}")
            for mail in mails:
                state.add_result(mail.id, 'failed', error=str(e))

    @transaction.atomic
    def _apply_classification(self, mail: Mail, result: dict, existing_folders: list) -> dict:
        """분류 결과 적용"""
        folder_path = result.get('folder_path', '미분류')
        is_new_folder = result.get('is_new_folder', False)
        confidence = result.get('confidence', 0.0)

        if folder_path == '미분류' or not folder_path:
            mail.is_classified = True
            mail.folder = None
            mail.save(update_fields=['is_classified', 'folder', 'updated_at'])
            return {
                'id': None,
                'name': '미분류',
                'path': '미분류',
                'is_new_folder': False,
                'confidence': confidence,
            }

        folder = None
        created = False

        if is_new_folder:
            folder, created = self._get_or_create_folder(folder_path)
        else:
            try:
                folder = Folder.objects.get(user=self.user, path=folder_path)
            except Folder.DoesNotExist:
                folder, created = self._get_or_create_folder(folder_path)

        # 메일에 폴더 할당
        old_folder = mail.folder
        mail.folder = folder
        mail.is_classified = True
        mail.save(update_fields=['folder', 'is_classified', 'updated_at'])

        # 폴더 카운트 업데이트
        if folder:
            folder.mail_count = Mail.objects.filter(
                user=self.user, folder=folder, is_deleted=False
            ).count()
            folder.unread_count = Mail.objects.filter(
                user=self.user, folder=folder, is_deleted=False, is_read=False
            ).count()
            folder.save(update_fields=['mail_count', 'unread_count'])

        if old_folder and old_folder != folder:
            old_folder.mail_count = Mail.objects.filter(
                user=self.user, folder=old_folder, is_deleted=False
            ).count()
            old_folder.unread_count = Mail.objects.filter(
                user=self.user, folder=old_folder, is_deleted=False, is_read=False
            ).count()
            old_folder.save(update_fields=['mail_count', 'unread_count'])

        return {
            'id': folder.id if folder else None,
            'name': folder.name if folder else '미분류',
            'path': folder.path if folder else '미분류',
            'is_new_folder': created,
            'confidence': confidence,
        }

    def _get_or_create_folder(self, folder_path: str) -> tuple:
        """폴더 생성 또는 조회 (경로 기반)"""
        parts = folder_path.split('/')
        parent = None
        created = False

        for i, part in enumerate(parts):
            if i >= 5:  # 최대 5단계
                break

            current_path = '/'.join(parts[:i + 1])

            folder, was_created = Folder.objects.get_or_create(
                user=self.user,
                path=current_path,
                defaults={
                    'name': part,
                    'parent': parent,
                    'depth': i,
                    'order': Folder.objects.filter(user=self.user, parent=parent).count(),
                }
            )

            if was_created:
                created = True
                logger.info(f"Created new folder: {current_path} for user {self.user.id}")

            parent = folder

        return parent, created
