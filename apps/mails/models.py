from django.db import models
from django.conf import settings


class Mail(models.Model):
    """Gmail 메일"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mails'
    )
    folder = models.ForeignKey(
        'folders.Folder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mails'
    )

    # Gmail 식별자
    gmail_id = models.CharField(max_length=50)  # Gmail Message ID
    thread_id = models.CharField(max_length=50)  # Gmail Thread ID

    # 메일 내용
    subject = models.CharField(max_length=500, blank=True)
    sender = models.CharField(max_length=200)  # "이름 <email@example.com>"
    sender_email = models.EmailField()
    recipients = models.JSONField(default=list)  # To, CC 수신자 목록
    # [{"type": "to", "email": "a@test.com", "name": "홍길동"}, {"type": "cc", ...}]
    snippet = models.TextField(blank=True)  # 미리보기 텍스트
    body_html = models.TextField(blank=True)  # HTML 본문

    # 첨부파일 메타데이터
    attachments = models.JSONField(default=list)
    # [{"id": "xxx", "name": "file.pdf", "size": 1024, "mimeType": "application/pdf"}]
    has_attachments = models.BooleanField(default=False)

    # 분류 상태
    is_classified = models.BooleanField(default=False)

    # 상태
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)  # Soft delete

    # 시간
    received_at = models.DateTimeField()  # Gmail internalDate
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mails'
        verbose_name = '메일'
        verbose_name_plural = '메일들'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['user', 'gmail_id']),
            models.Index(fields=['user', 'folder', '-received_at']),
            models.Index(fields=['user', 'is_read', '-received_at']),
            models.Index(fields=['user', 'is_classified']),
            models.Index(fields=['user', '-received_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'gmail_id'],
                name='unique_user_gmail_id'
            )
        ]

    def __str__(self):
        return f"{self.subject[:50]}..." if len(self.subject) > 50 else self.subject
