"""
소프트 초기화 명령어 - 분류 상태와 폴더만 초기화 (메일 데이터는 유지)
"""
from django.core.management.base import BaseCommand

from apps.folders.models import Folder
from apps.mails.models import Mail


class Command(BaseCommand):
    help = '메일 분류 상태 초기화 및 폴더 삭제 (메일 데이터는 유지)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--folders-only',
            action='store_true',
            help='폴더만 삭제 (메일 분류 상태는 유지)',
        )
        parser.add_argument(
            '--mails-only',
            action='store_true',
            help='메일 분류 상태만 초기화 (폴더는 유지)',
        )

    def handle(self, *args, **options):
        folders_only = options.get('folders_only', False)
        mails_only = options.get('mails_only', False)

        # 둘 다 지정 안 하면 전체 초기화
        reset_mails = not folders_only
        reset_folders = not mails_only

        if reset_mails:
            mail_count = Mail.objects.update(is_classified=False, folder=None)
            self.stdout.write(
                self.style.SUCCESS(f'메일 분류 초기화: {mail_count}개')
            )

        if reset_folders:
            folder_count = Folder.objects.count()
            Folder.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f'폴더 삭제: {folder_count}개')
            )

        self.stdout.write(self.style.SUCCESS('소프트 초기화 완료!'))
