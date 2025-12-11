from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['분류'])
class ClassifyView(APIView):
    """메일 분류 요청"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='메일 분류 요청',
        description='특정 메일의 분류를 요청합니다 (수동 재분류).',
    )
    def post(self, request):
        # TODO: 분류 로직 구현
        return Response({
            'status': 'error',
            'message': 'Not implemented yet'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


@extend_schema(tags=['분류'])
class ClassifyUnclassifiedView(APIView):
    """미분류 메일 일괄 분류"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='미분류 메일 일괄 분류',
        description='미분류 상태인 모든 메일을 분류합니다.',
    )
    def post(self, request):
        # TODO: 일괄 분류 로직 구현
        return Response({
            'status': 'error',
            'message': 'Not implemented yet'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
