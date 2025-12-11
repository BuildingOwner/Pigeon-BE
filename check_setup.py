#!/usr/bin/env python
"""
Pigeon Backend Setup Checker

이 스크립트는 Phase 1 개발이 올바르게 완료되었는지 확인합니다.
"""

import os
import sys
from pathlib import Path

# Django 설정 로드
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Django setup
import django
django.setup()

from django.conf import settings
from django.core.management import call_command
from apps.accounts.models import User
from apps.folders.models import Folder
from apps.mails.models import Mail


def print_header(title):
    """섹션 헤더 출력"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_environment():
    """환경 변수 확인"""
    print_header("1. 환경 변수 확인")

    required_vars = [
        'SECRET_KEY',
        'TOKEN_ENCRYPTION_KEY',
    ]

    optional_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'GOOGLE_API_KEY',
    ]

    print("\n필수 환경 변수:")
    for var in required_vars:
        value = os.environ.get(var, '')
        status = "✓" if value and value != f'your-{var.lower().replace("_", "-")}-here' else "✗"
        masked_value = value[:20] + '...' if len(value) > 20 else value
        print(f"  {status} {var}: {masked_value if value else '(not set)'}")

    print("\n선택 환경 변수 (Google API):")
    for var in optional_vars:
        value = os.environ.get(var, '')
        status = "✓" if value and not value.startswith('your-') else "○"
        masked_value = value[:20] + '...' if len(value) > 20 else value
        print(f"  {status} {var}: {masked_value if value else '(not set)'}")


def check_models():
    """모델 확인"""
    print_header("2. 모델 확인")

    models = [
        ('User', User),
        ('Folder', Folder),
        ('Mail', Mail),
    ]

    for name, model in models:
        try:
            count = model.objects.count()
            print(f"  ✓ {name}: {count} 레코드")
        except Exception as e:
            print(f"  ✗ {name}: 에러 - {str(e)[:50]}")


def check_database():
    """데이터베이스 마이그레이션 확인"""
    print_header("3. 데이터베이스 마이그레이션")

    try:
        call_command('showmigrations', '--list')
        print("\n  ✓ 마이그레이션 확인 완료")
    except Exception as e:
        print(f"\n  ✗ 마이그레이션 에러: {e}")


def check_apps():
    """설치된 앱 확인"""
    print_header("4. 설치된 Django 앱")

    local_apps = [
        'apps.accounts',
        'apps.folders',
        'apps.mails',
        'apps.classifier',
    ]

    for app in local_apps:
        status = "✓" if app in settings.INSTALLED_APPS else "✗"
        print(f"  {status} {app}")


def check_rest_framework():
    """REST Framework 설정 확인"""
    print_header("5. REST Framework 설정")

    if hasattr(settings, 'REST_FRAMEWORK'):
        print("  ✓ REST_FRAMEWORK 설정 있음")

        important_settings = [
            'DEFAULT_AUTHENTICATION_CLASSES',
            'DEFAULT_PERMISSION_CLASSES',
            'DEFAULT_SCHEMA_CLASS',
        ]

        for key in important_settings:
            value = settings.REST_FRAMEWORK.get(key)
            if value:
                print(f"    - {key}: ✓")
            else:
                print(f"    - {key}: ✗")
    else:
        print("  ✗ REST_FRAMEWORK 설정 없음")


def check_spectacular():
    """Swagger 설정 확인"""
    print_header("6. Swagger (drf-spectacular) 설정")

    if hasattr(settings, 'SPECTACULAR_SETTINGS'):
        print("  ✓ SPECTACULAR_SETTINGS 설정 있음")
        title = settings.SPECTACULAR_SETTINGS.get('TITLE', '')
        version = settings.SPECTACULAR_SETTINGS.get('VERSION', '')
        print(f"    - Title: {title}")
        print(f"    - Version: {version}")
    else:
        print("  ✗ SPECTACULAR_SETTINGS 설정 없음")


def print_summary():
    """최종 요약"""
    print_header("✅ 설정 확인 완료")

    print("\n다음 단계:")
    print("  1. 마이그레이션 실행: python manage.py migrate")
    print("  2. 개발 서버 실행: python manage.py runserver")
    print("  3. Swagger 접속: http://localhost:8000/api/v1/docs/")
    print("\n" + "=" * 60 + "\n")


def main():
    """메인 실행"""
    print("\n🕊️ Pigeon Backend - Setup Checker")
    print("=" * 60)

    try:
        check_environment()
        check_apps()
        check_rest_framework()
        check_spectacular()

        # 마이그레이션 상태 확인 (DB가 있을 때만)
        db_file = BASE_DIR / 'db.sqlite3'
        if db_file.exists():
            check_database()
            check_models()
        else:
            print_header("데이터베이스")
            print("  ⚠️  db.sqlite3 파일이 없습니다.")
            print("  → 'python manage.py migrate'를 실행하세요.")

        print_summary()

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
