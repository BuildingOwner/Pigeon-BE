"""
커스텀 예외 및 예외 핸들러
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


class PigeonException(Exception):
    """Pigeon 커스텀 예외 베이스 클래스"""
    default_code = 'ERROR'
    default_message = '오류가 발생했습니다.'
    default_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, message=None, code=None, status_code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.status_code = status_code or self.default_status
        super().__init__(self.message)


class OAuthException(PigeonException):
    """OAuth 인증 예외"""
    default_code = 'OAUTH_FAILED'
    default_message = 'OAuth 인증에 실패했습니다.'
    default_status = status.HTTP_401_UNAUTHORIZED


class GmailAPIException(PigeonException):
    """Gmail API 예외"""
    default_code = 'GMAIL_API_ERROR'
    default_message = 'Gmail API 호출 중 오류가 발생했습니다.'
    default_status = status.HTTP_502_BAD_GATEWAY


class ClassificationException(PigeonException):
    """분류 예외"""
    default_code = 'CLASSIFICATION_FAILED'
    default_message = '메일 분류에 실패했습니다.'
    default_status = status.HTTP_500_INTERNAL_SERVER_ERROR


def custom_exception_handler(exc, context):
    """
    커스텀 예외 핸들러
    DRF의 기본 예외 핸들러를 확장하여 일관된 에러 응답 형식을 제공합니다.
    """
    # DRF 기본 예외 처리
    response = exception_handler(exc, context)

    if response is not None:
        # DRF 기본 예외를 표준 형식으로 변환
        error_data = {
            'status': 'error',
            'code': getattr(exc, 'default_code', 'ERROR'),
            'message': str(exc),
        }

        if isinstance(response.data, dict):
            error_data['details'] = response.data

        response.data = error_data
        return response

    # Pigeon 커스텀 예외 처리
    if isinstance(exc, PigeonException):
        return Response(
            {
                'status': 'error',
                'code': exc.code,
                'message': exc.message,
            },
            status=exc.status_code
        )

    # 기타 예외는 기본 핸들러에 위임
    return None
