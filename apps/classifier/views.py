"""
분류 API Views
"""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ClassificationStartResponseSerializer,
    ClassificationStatusResponseSerializer,
    ClassifyRequestSerializer,
)
from .services import ClassificationState, ClassifierService


@extend_schema(tags=['분류'])
class ClassifyView(APIView):
    """메일 분류 요청"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='메일 분류 요청',
        description='특정 메일의 분류를 요청합니다 (수동 재분류).',
        request=ClassifyRequestSerializer,
        responses={
            202: OpenApiResponse(
                response=ClassificationStartResponseSerializer,
                description='분류 시작'
            ),
            400: OpenApiResponse(description='잘못된 요청'),
        },
    )
    def post(self, request):
        serializer = ClassifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mail_ids = serializer.validated_data['mail_ids']

        service = ClassifierService(request.user)
        result = service.classify_mails(mail_ids)

        if result.get('status') == 'no_mails':
            return Response({
                'status': 'error',
                'code': 'NO_MAILS',
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'success',
            'data': result
        }, status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=['분류'])
class ClassifyUnclassifiedView(APIView):
    """미분류 메일 일괄 분류"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='미분류 메일 일괄 분류',
        description='미분류 상태인 모든 메일을 분류합니다.',
        responses={
            202: OpenApiResponse(
                response=ClassificationStartResponseSerializer,
                description='분류 시작'
            ),
            400: OpenApiResponse(description='분류할 메일 없음'),
        },
    )
    def post(self, request):
        service = ClassifierService(request.user)
        result = service.classify_unclassified()

        if result.get('status') == 'no_mails':
            return Response({
                'status': 'error',
                'code': 'NO_UNCLASSIFIED_MAILS',
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'success',
            'data': result
        }, status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=['분류'])
class ClassificationStatusView(APIView):
    """분류 결과 조회"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='분류 결과 조회',
        description='분류 작업 결과를 조회합니다.',
        responses={
            200: OpenApiResponse(
                response=ClassificationStatusResponseSerializer,
                description='분류 결과'
            ),
            404: OpenApiResponse(description='분류 작업 없음'),
        },
    )
    def get(self, request, classification_id):
        state = ClassificationState.get(classification_id)

        if not state:
            return Response({
                'status': 'error',
                'code': 'NOT_FOUND',
                'message': '분류 작업을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)

        if state.user_id != request.user.id:
            return Response({
                'status': 'error',
                'code': 'FORBIDDEN',
                'message': '접근 권한이 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'status': 'success',
            'data': state.to_dict()
        })


@extend_schema(tags=['분류'])
class ClassificationStopView(APIView):
    """분류 작업 중단"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='분류 작업 중단',
        description='진행 중인 분류 작업을 중단합니다.',
        responses={
            200: OpenApiResponse(description='중단 성공'),
            400: OpenApiResponse(description='중단할 수 없는 상태'),
            404: OpenApiResponse(description='분류 작업 없음'),
        },
    )
    def post(self, request, classification_id):
        state = ClassificationState.get(classification_id)

        if not state:
            return Response({
                'status': 'error',
                'code': 'NOT_FOUND',
                'message': '분류 작업을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)

        if state.user_id != request.user.id:
            return Response({
                'status': 'error',
                'code': 'FORBIDDEN',
                'message': '접근 권한이 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)

        # 이미 완료/취소된 상태면 성공으로 처리
        if state.state in ('completed', 'cancelled'):
            return Response({
                'status': 'success',
                'message': '분류 작업이 이미 완료되었습니다.',
                'data': state.to_dict()
            })

        if state.state not in ('in_progress', 'pending'):
            return Response({
                'status': 'error',
                'code': 'INVALID_STATE',
                'message': f'현재 상태({state.state})에서는 중단할 수 없습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        state.cancel()

        return Response({
            'status': 'success',
            'message': '분류 작업이 중단되었습니다.',
            'data': state.to_dict()
        })
