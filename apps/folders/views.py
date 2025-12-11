from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Folder
from .serializers import FolderSerializer, FolderTreeSerializer


@extend_schema_view(
    list=extend_schema(
        summary='폴더 목록 조회',
        description='사용자의 모든 폴더를 조회합니다. flat=true 시 평탄화된 리스트, 아니면 트리 구조로 반환합니다.',
        tags=['폴더']
    ),
    create=extend_schema(
        summary='폴더 생성',
        description='새 폴더를 생성합니다. 최대 5단계 깊이까지 허용됩니다.',
        tags=['폴더']
    ),
    retrieve=extend_schema(
        summary='폴더 상세 조회',
        description='특정 폴더의 상세 정보를 조회합니다.',
        tags=['폴더']
    ),
    update=extend_schema(
        summary='폴더 수정',
        description='폴더 정보를 수정합니다. 순환 참조는 허용되지 않습니다.',
        tags=['폴더']
    ),
    partial_update=extend_schema(
        summary='폴더 부분 수정',
        description='폴더 정보를 부분적으로 수정합니다. 순환 참조는 허용되지 않습니다.',
        tags=['폴더']
    ),
    destroy=extend_schema(
        summary='폴더 삭제',
        description='폴더를 삭제합니다. 하위 폴더와 메일은 미분류로 이동합니다.',
        tags=['폴더']
    ),
)
class FolderViewSet(viewsets.ModelViewSet):
    """폴더 ViewSet"""
    permission_classes = [IsAuthenticated]
    serializer_class = FolderSerializer

    def get_queryset(self):
        return Folder.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def list(self, request, *args, **kwargs):
        folders = self.get_queryset()
        flat = request.query_params.get('flat', 'false').lower() == 'true'

        if flat:
            serializer = FolderSerializer(folders, many=True)
            return Response({
                'status': 'success',
                'data': {
                    'folders': serializer.data
                }
            })
        else:
            # 트리 구조 생성
            folder_list = list(folders)
            folder_map = {f.id: f for f in folder_list}

            # children_list 속성 추가
            for folder in folder_list:
                folder.children_list = []

            # 트리 구조 구성
            root_folders = []
            for folder in folder_list:
                if folder.parent_id and folder.parent_id in folder_map:
                    folder_map[folder.parent_id].children_list.append(folder)
                else:
                    root_folders.append(folder)

            serializer = FolderTreeSerializer(root_folders, many=True)

            # 전체 통계 계산
            total_mail_count = sum(f.mail_count for f in folder_list)
            total_unread_count = sum(f.unread_count for f in folder_list)

            return Response({
                'status': 'success',
                'data': {
                    'folders': serializer.data,
                    'total_mail_count': total_mail_count,
                    'total_unread_count': total_unread_count,
                }
            })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 사용자 설정
        folder = serializer.save(user=request.user)

        return Response({
            'status': 'success',
            'data': FolderSerializer(folder).data
        }, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """폴더 삭제 시 하위 폴더와 메일을 미분류로 이동"""
        folder = self.get_object()

        # 이 폴더와 모든 하위 폴더 ID 수집
        folder_ids = [folder.id]
        self._collect_descendant_ids(folder, folder_ids)

        # 메일들을 미분류(folder=None)로 이동
        from apps.mails.models import Mail
        moved_mails_count = Mail.objects.filter(
            folder_id__in=folder_ids,
            user=request.user
        ).update(folder=None, is_classified=False)

        # 하위 폴더들을 루트로 이동 (부모 폴더만 삭제하는 경우)
        moved_subfolders_count = Folder.objects.filter(
            parent=folder,
            user=request.user
        ).count()

        # 하위 폴더를 미분류(루트)로 이동
        Folder.objects.filter(
            parent=folder,
            user=request.user
        ).update(parent=None, depth=0)

        # 하위로 이동된 폴더들의 path 재계산
        for child in Folder.objects.filter(parent=None, user=request.user).exclude(id=folder.id):
            self._update_path_recursive(child)

        # 폴더 삭제
        folder.delete()

        return Response({
            'status': 'success',
            'message': '폴더가 삭제되었습니다.',
            'data': {
                'moved_mails_count': moved_mails_count,
                'moved_subfolders_count': moved_subfolders_count
            }
        })

    def _collect_descendant_ids(self, folder, id_list):
        """하위 폴더 ID를 재귀적으로 수집"""
        for child in Folder.objects.filter(parent=folder):
            id_list.append(child.id)
            self._collect_descendant_ids(child, id_list)

    def _update_path_recursive(self, folder):
        """폴더와 하위 폴더의 path를 재귀적으로 업데이트"""
        if folder.parent:
            folder.depth = folder.parent.depth + 1
            folder.path = f"{folder.parent.path}/{folder.name}"
        else:
            folder.depth = 0
            folder.path = folder.name
        folder.save(update_fields=['depth', 'path'])

        for child in Folder.objects.filter(parent=folder):
            self._update_path_recursive(child)

    @extend_schema(
        summary='폴더 순서 변경',
        description='여러 폴더의 순서를 한번에 변경합니다.',
        tags=['폴더'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'orders': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'order': {'type': 'integer'}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['put'])
    def reorder(self, request):
        orders = request.data.get('orders', [])

        for item in orders:
            folder_id = item.get('id')
            order = item.get('order')

            try:
                folder = Folder.objects.get(id=folder_id, user=request.user)
                folder.order = order
                folder.save(update_fields=['order'])
            except Folder.DoesNotExist:
                continue

        return Response({
            'status': 'success',
            'message': '폴더 순서가 변경되었습니다.'
        })
