from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Mail
from .serializers import MailListSerializer, MailDetailSerializer, MailUpdateSerializer


@extend_schema_view(
    list=extend_schema(
        summary='메일 목록 조회',
        description='메일 목록을 조회합니다. 폴더별, 읽음 상태별 필터링을 지원합니다.',
        tags=['메일']
    ),
    retrieve=extend_schema(
        summary='메일 상세 조회',
        description='메일 상세 내용을 조회합니다. 조회 시 자동으로 읽음 처리됩니다.',
        tags=['메일']
    ),
    partial_update=extend_schema(
        summary='메일 상태 수정',
        description='메일의 읽음/별표 상태를 변경합니다.',
        tags=['메일']
    ),
    destroy=extend_schema(
        summary='메일 삭제',
        description='메일을 삭제합니다 (Soft Delete).',
        tags=['메일']
    ),
)
class MailViewSet(viewsets.ModelViewSet):
    """메일 ViewSet"""
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'delete', 'post']

    def get_queryset(self):
        queryset = Mail.objects.filter(user=self.request.user, is_deleted=False)

        # 폴더 필터
        folder_id = self.request.query_params.get('folder_id')
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)

        # 읽음 상태 필터
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        # 별표 필터
        is_starred = self.request.query_params.get('is_starred')
        if is_starred is not None:
            queryset = queryset.filter(is_starred=is_starred.lower() == 'true')

        # 분류 상태 필터
        is_classified = self.request.query_params.get('is_classified')
        if is_classified is not None:
            queryset = queryset.filter(is_classified=is_classified.lower() == 'true')

        # 검색
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(subject__icontains=search) |
                models.Q(sender__icontains=search) |
                models.Q(snippet__icontains=search)
            )

        return queryset.select_related('folder')

    def get_serializer_class(self):
        if self.action == 'list':
            return MailListSerializer
        elif self.action in ['partial_update', 'update']:
            return MailUpdateSerializer
        return MailDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response({
                'status': 'success',
                'data': paginated_response.data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'data': {'mails': serializer.data}
        })

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # 자동 읽음 처리
        if not instance.is_read:
            instance.is_read = True
            instance.save(update_fields=['is_read'])

        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'status': 'success',
            'data': {
                'id': instance.id,
                'is_read': instance.is_read,
                'is_starred': instance.is_starred,
                'updated_at': instance.updated_at,
            }
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

        return Response({
            'status': 'success',
            'message': '메일이 삭제되었습니다.'
        })

    @extend_schema(
        summary='메일 폴더 이동',
        description='메일을 다른 폴더로 이동합니다.',
        tags=['메일'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'folder_id': {'type': 'integer', 'nullable': True}
                }
            }
        }
    )
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        mail = self.get_object()
        folder_id = request.data.get('folder_id')

        if folder_id:
            from apps.folders.models import Folder
            try:
                folder = Folder.objects.get(id=folder_id, user=request.user)
                mail.folder = folder
            except Folder.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': '폴더를 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            mail.folder = None

        mail.save(update_fields=['folder'])

        return Response({
            'status': 'success',
            'data': {
                'id': mail.id,
                'folder': {
                    'id': mail.folder.id,
                    'name': mail.folder.name,
                    'path': mail.folder.path
                } if mail.folder else None,
                'updated_at': mail.updated_at,
            }
        })

    @extend_schema(
        summary='메일 일괄 이동',
        description='여러 메일을 한번에 다른 폴더로 이동합니다.',
        tags=['메일'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'mail_ids': {'type': 'array', 'items': {'type': 'integer'}},
                    'folder_id': {'type': 'integer'}
                }
            }
        }
    )
    @action(detail=False, methods=['post'])
    def bulk_move(self, request):
        mail_ids = request.data.get('mail_ids', [])
        folder_id = request.data.get('folder_id')

        if not mail_ids:
            return Response({
                'status': 'error',
                'message': 'mail_ids가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        from apps.folders.models import Folder
        try:
            folder = Folder.objects.get(id=folder_id, user=request.user)
        except Folder.DoesNotExist:
            return Response({
                'status': 'error',
                'message': '폴더를 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)

        updated_count = Mail.objects.filter(
            id__in=mail_ids,
            user=request.user
        ).update(folder=folder)

        return Response({
            'status': 'success',
            'data': {
                'moved_count': updated_count,
                'folder': {
                    'id': folder.id,
                    'name': folder.name,
                    'path': folder.path,
                }
            }
        })

    @extend_schema(
        summary='메일 일괄 상태 변경',
        description='여러 메일의 읽음/별표 상태를 한번에 변경합니다.',
        tags=['메일'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'mail_ids': {'type': 'array', 'items': {'type': 'integer'}},
                    'is_read': {'type': 'boolean', 'nullable': True},
                    'is_starred': {'type': 'boolean', 'nullable': True}
                }
            }
        }
    )
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        mail_ids = request.data.get('mail_ids', [])

        if not mail_ids:
            return Response({
                'status': 'error',
                'message': 'mail_ids가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        update_data = {}
        if 'is_read' in request.data:
            update_data['is_read'] = request.data['is_read']
        if 'is_starred' in request.data:
            update_data['is_starred'] = request.data['is_starred']

        if not update_data:
            return Response({
                'status': 'error',
                'message': '업데이트할 필드가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        updated_count = Mail.objects.filter(
            id__in=mail_ids,
            user=request.user
        ).update(**update_data)

        return Response({
            'status': 'success',
            'data': {
                'updated_count': updated_count
            }
        })
