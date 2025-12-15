"""
LLM API 클라이언트 (Gemini 우선, OpenAI GPT 폴백)
"""
import json
import logging
import re
import time

from django.conf import settings
from rest_framework.exceptions import ValidationError

from ..prompts import BATCH_CLASSIFICATION_PROMPT, CLASSIFICATION_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM API 클라이언트 (Gemini 우선, GPT 폴백) - LangChain 통합"""

    def __init__(self):
        self.primary_llm = None
        self.fallback_llm = None
        self.primary_provider = None
        self.fallback_provider = None

        google_api_key = getattr(settings, 'GOOGLE_API_KEY', None)
        openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)

        # Gemini 우선 초기화
        if google_api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                model = "gemini-2.5-flash"
                self.primary_llm = ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=google_api_key,
                    temperature=0.1,
                    max_tokens=2048,
                )
                self.primary_provider = model
                logger.info("Primary LLM: Google Gemini (LangChain)")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        # OpenAI를 폴백으로 초기화
        if openai_api_key:
            try:
                from langchain_openai import ChatOpenAI
                model="gpt-5-nano"
                self.fallback_llm = ChatOpenAI(
                    model=model,
                    api_key=openai_api_key,
                    temperature=0.1,
                    max_tokens=2048,
                )
                self.fallback_provider = model
                logger.info("Fallback LLM: OpenAI GPT (LangChain)")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        # Primary가 없으면 fallback을 primary로 승격
        if self.primary_llm is None and self.fallback_llm is not None:
            self.primary_llm = self.fallback_llm
            self.primary_provider = self.fallback_provider
            self.fallback_llm = None
            self.fallback_provider = None
            logger.info(f"Promoted {self.primary_provider} to primary (no Gemini available)")

        if self.primary_llm is None:
            raise ValidationError({
                'code': 'LLM_NOT_CONFIGURED',
                'message': 'GOOGLE_API_KEY 또는 OPENAI_API_KEY가 설정되지 않았습니다.'
            })

        # 호환성을 위한 속성
        self.llm = self.primary_llm
        self.provider = self.primary_provider

    def classify_mail(self, mail_data: dict, existing_folders: list) -> dict:
        """
        단일 메일 분류
        """
        folders_str = self._format_folders(existing_folders)
        prompt = CLASSIFICATION_PROMPT.format(
            folders=folders_str,
            subject=mail_data.get('subject', '(제목 없음)'),
            sender=mail_data.get('sender', '(알 수 없음)'),
            snippet=mail_data.get('snippet', '')[:500]
        )

        try:
            response = self._invoke_with_retry(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            raise ValidationError({
                'code': 'LLM_API_ERROR',
                'message': f'AI 분류 실패: {str(e)}'
            })

    def classify_mails_batch(self, mails_data: list, existing_folders: list) -> list:
        """
        배치 메일 분류 (최대 20개)
        """
        if len(mails_data) > 20:
            mails_data = mails_data[:20]

        folders_str = self._format_folders(existing_folders)
        emails_str = self._format_emails(mails_data)

        prompt = BATCH_CLASSIFICATION_PROMPT.format(
            folders=folders_str,
            emails=emails_str
        )

        try:
            response = self._invoke_with_retry(prompt)
            return self._parse_batch_response(response, mails_data)
        except Exception as e:
            logger.error(f"LLM batch classification failed: {e}")
            raise ValidationError({
                'code': 'LLM_API_ERROR',
                'message': f'AI 배치 분류 실패: {str(e)}'
            })

    def _invoke_with_retry(self, prompt: str, max_retries: int = 2) -> str:
        """LLM 호출 (재시도 포함, 폴백 지원)"""
        last_error = None

        # Primary LLM 시도
        for attempt in range(max_retries):
            try:
                result = self._invoke_llm(prompt, self.primary_llm, self.primary_provider)
                self.provider = self.primary_provider  # 실제 사용된 provider 기록
                return result
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                logger.warning(f"Primary LLM ({self.primary_provider}) attempt {attempt + 1} failed: {e}")

                # 429, rate limit, 연결 에러 체크
                is_retriable = (
                    '429' in error_str or
                    'rate' in error_str or
                    'resource_exhausted' in error_str or
                    'quota' in error_str or
                    'connection' in error_str or
                    'timeout' in error_str
                )

                if is_retriable:
                    wait_time = (2 ** attempt) * 2  # 2초, 4초
                    logger.info(f"Retriable error, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    time.sleep(1)

        # Fallback LLM 시도
        if self.fallback_llm is not None:
            logger.info(f"Switching to fallback LLM ({self.fallback_provider})")
            for attempt in range(max_retries):
                try:
                    result = self._invoke_llm(prompt, self.fallback_llm, self.fallback_provider)
                    self.provider = self.fallback_provider  # 실제 사용된 provider 기록
                    return result
                except Exception as e:
                    last_error = e
                    logger.warning(f"Fallback LLM ({self.fallback_provider}) attempt {attempt + 1} failed: {e}")
                    time.sleep(2 ** attempt)

        raise last_error

    def _invoke_llm(self, prompt: str, llm=None, provider: str = None) -> str:
        """LangChain 통합 LLM 호출"""
        if llm is None:
            llm = self.primary_llm
            provider = self.primary_provider

        messages = [
            ("system", SYSTEM_PROMPT),
            ("human", prompt)
        ]
        logger.debug(f"Invoking {provider} LLM...")
        response = llm.invoke(messages)
        return response.content

    def _format_folders(self, folders: list) -> str:
        """폴더 목록 포맷팅"""
        if not folders:
            return "(폴더 없음 - 새 폴더를 제안해주세요)"
        return "\n".join([f"- {f['path']}" for f in folders])

    def _format_emails(self, mails: list) -> str:
        """이메일 목록 포맷팅"""
        result = []
        for mail in mails:
            result.append(f"""### 이메일 #{mail['id']}
- 제목: {mail.get('subject', '(제목 없음)')}
- 발신자: {mail.get('sender', '(알 수 없음)')}
- 내용: {mail.get('snippet', '')[:200]}
""")
        return "\n".join(result)

    def _parse_response(self, response: str) -> dict:
        """단일 분류 응답 파싱"""
        try:
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    'folder_path': data.get('folder_path', '미분류'),
                    'is_new_folder': data.get('is_new_folder', False),
                    'confidence': float(data.get('confidence', 0.5)),
                    'reason': data.get('reason', '')
                }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")

        return {
            'folder_path': '미분류',
            'is_new_folder': False,
            'confidence': 0.0,
            'reason': 'AI 응답 파싱 실패'
        }

    def _parse_batch_response(self, response: str, mails_data: list) -> list:
        """배치 분류 응답 파싱"""
        try:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
                results = []
                for item in data:
                    results.append({
                        'mail_id': item.get('mail_id'),
                        'folder_path': item.get('folder_path', '미분류'),
                        'is_new_folder': item.get('is_new_folder', False),
                        'confidence': float(item.get('confidence', 0.5)),
                        'reason': item.get('reason', '')
                    })
                return results
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse batch response: {e}")

        return [
            {
                'mail_id': mail['id'],
                'folder_path': '미분류',
                'is_new_folder': False,
                'confidence': 0.0,
                'reason': 'AI 응답 파싱 실패'
            }
            for mail in mails_data
        ]
