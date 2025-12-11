"""
Sync Views
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SyncStartSerializer, SyncStatusSerializer
from .services import GmailSyncService


class SyncStartView(APIView):
    """동기화 시작 API"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='동기화 시작',
        description='Gmail 메일 동기화를 시작합니다. 최초 실행 시 6개월치 메일을 동기화합니다.',
        request=SyncStartSerializer,
        responses={
            202: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'sync_id': {'type': 'string'},
                            'type': {'type': 'string'},
                            'started_at': {'type': 'string'},
                        }
                    }
                }
            }
        },
        tags=['동기화']
    )
    def post(self, request):
        serializer = SyncStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        full_sync = serializer.validated_data.get('full_sync', False)

        try:
            sync_service = GmailSyncService(request.user)
            result = sync_service.start_sync(full_sync=full_sync)

            if result.get('status') == 'already_running':
                return Response({
                    'status': 'error',
                    'code': 'SYNC_ALREADY_RUNNING',
                    'message': '이미 동기화가 진행 중입니다.',
                    'data': {'sync_id': result.get('sync_id')}
                }, status=status.HTTP_409_CONFLICT)

            return Response({
                'status': 'success',
                'data': result
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response({
                'status': 'error',
                'code': 'SYNC_FAILED',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncStatusView(APIView):
    """동기화 상태 조회 API"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='동기화 상태 조회',
        description='현재 동기화 진행 상태를 조회합니다.',
        responses={
            200: SyncStatusSerializer
        },
        tags=['동기화']
    )
    def get(self, request):
        sync_service = GmailSyncService(request.user)
        result = sync_service.get_status()

        return Response({
            'status': 'success',
            'data': result
        })


class SyncStopView(APIView):
    """동기화 중단 API"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='동기화 중단',
        description='진행 중인 동기화를 중단합니다.',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'sync_id': {'type': 'string'},
                            'synced_count': {'type': 'integer'},
                        }
                    }
                }
            }
        },
        tags=['동기화']
    )
    def post(self, request):
        sync_service = GmailSyncService(request.user)
        result = sync_service.stop_sync()

        if result.get('status') == 'not_running':
            return Response({
                'status': 'error',
                'code': 'SYNC_NOT_RUNNING',
                'message': result.get('message')
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'success',
            'message': '동기화가 중단되었습니다.',
            'data': result
        })
