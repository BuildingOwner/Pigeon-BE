from django.conf import settings
from django.db import models


class Folder(models.Model):
    """메일 분류 폴더 (트리 구조)"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='folders'
    )

    # 트리 구조
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    path = models.CharField(max_length=500)  # 전체 경로: "업무/프로젝트A/회의록"
    depth = models.PositiveSmallIntegerField(default=0)  # 깊이 (0=루트)

    # 통계 (캐시)
    mail_count = models.PositiveIntegerField(default=0)
    unread_count = models.PositiveIntegerField(default=0)

    # 정렬
    order = models.PositiveIntegerField(default=0)

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'folders'
        verbose_name = '폴더'
        verbose_name_plural = '폴더들'
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['user', 'path']),
            models.Index(fields=['user', 'parent']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'path'],
                name='unique_user_folder_path'
            )
        ]

    def __str__(self):
        return self.path

    def save(self, *args, **kwargs):
        # 깊이 자동 계산
        if self.parent:
            self.depth = self.parent.depth + 1
            self.path = f"{self.parent.path}/{self.name}"
        else:
            self.depth = 0
            self.path = self.name
        super().save(*args, **kwargs)
