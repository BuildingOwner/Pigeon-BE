from rest_framework import serializers

from .models import Folder

MAX_FOLDER_DEPTH = 4  # 0~4단계 = 5단계


class FolderSerializer(serializers.ModelSerializer):
    """폴더 Serializer"""
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Folder
        fields = [
            'id',
            'name',
            'path',
            'depth',
            'parent_id',
            'mail_count',
            'unread_count',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'path', 'depth', 'created_at', 'updated_at']

    def validate_parent_id(self, value):
        """부모 폴더 유효성 검사"""
        if value is None:
            return value

        request = self.context.get('request')
        if not request:
            return value

        try:
            parent = Folder.objects.get(id=value, user=request.user)
        except Folder.DoesNotExist:
            raise serializers.ValidationError("상위 폴더를 찾을 수 없습니다.")

        # 깊이 제한 검사
        if parent.depth >= MAX_FOLDER_DEPTH:
            raise serializers.ValidationError(
                f"최대 폴더 깊이({MAX_FOLDER_DEPTH + 1}단계)를 초과합니다."
            )

        # 순환 참조 검사 (수정 시에만)
        if self.instance:
            current_folder = self.instance
            # 자기 자신으로 이동 불가
            if parent.id == current_folder.id:
                raise serializers.ValidationError("폴더를 자기 자신의 하위로 이동할 수 없습니다.")

            # 자신의 하위 폴더로 이동 불가
            if self._is_descendant(current_folder, parent):
                raise serializers.ValidationError("폴더를 자신의 하위 폴더로 이동할 수 없습니다.")

        return value

    def _is_descendant(self, ancestor, folder):
        """folder가 ancestor의 하위 폴더인지 확인"""
        current = folder
        while current.parent_id:
            if current.parent_id == ancestor.id:
                return True
            try:
                current = Folder.objects.get(id=current.parent_id)
            except Folder.DoesNotExist:
                break
        return False

    def create(self, validated_data):
        parent_id = validated_data.pop('parent_id', None)
        if parent_id:
            validated_data['parent'] = Folder.objects.get(id=parent_id)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        parent_id = validated_data.pop('parent_id', None)
        if 'parent_id' in self.initial_data:
            if parent_id:
                validated_data['parent'] = Folder.objects.get(id=parent_id)
            else:
                validated_data['parent'] = None
        return super().update(instance, validated_data)


class FolderTreeSerializer(serializers.ModelSerializer):
    """폴더 트리 Serializer (재귀)"""
    children = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            'id',
            'name',
            'path',
            'depth',
            'mail_count',
            'unread_count',
            'order',
            'children',
        ]

    def get_children(self, obj):
        if hasattr(obj, 'children_list'):
            return FolderTreeSerializer(obj.children_list, many=True).data
        return []
