# Pigeon Backend (Django)

Gmail AI 메일 폴더링 시스템의 백엔드 API 서버입니다.

## 기술 스택

- **Framework**: Django 5.0 + Django REST Framework
- **Database**: SQLite3
- **Authentication**: JWT (djangorestframework-simplejwt)
- **AI/LLM**: LangChain + Google Gemini 2.5 Flash
- **External API**: Google Gmail API, Google OAuth2
- **Documentation**: drf-spectacular (Swagger)

## 프로젝트 구조

```
Pigeon-BE/
├── config/                 # Django 설정
│   ├── settings/
│   │   ├── base.py        # 공통 설정
│   │   ├── development.py # 개발 환경
│   │   └── production.py  # 운영 환경
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                   # Django 앱
│   ├── accounts/          # 사용자 인증
│   ├── mails/             # 메일 관리
│   ├── folders/           # 폴더 관리
│   └── classifier/        # AI 분류
│
├── core/                   # 공통 유틸리티
│   ├── exceptions.py      # 커스텀 예외
│   ├── pagination.py      # 페이지네이션
│   └── permissions.py     # 권한 클래스
│
├── manage.py
├── requirements.txt
└── .env.example
```

## 설치 및 실행

### 빠른 시작 (Quick Start)

자동 설치 스크립트를 사용하면 쉽게 환경을 구성할 수 있습니다:

```bash
# Linux/macOS
chmod +x setup.sh
./setup.sh

# Windows
setup.bat
```

또는 아래 단계를 따라 수동으로 설치하세요.

### 1. 환경 변수 설정

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# .env 파일 편집
# 필수 환경 변수:
# - SECRET_KEY: Django 시크릿 키
# - TOKEN_ENCRYPTION_KEY: Fernet 암호화 키
# - GOOGLE_CLIENT_ID: Google OAuth 클라이언트 ID
# - GOOGLE_CLIENT_SECRET: Google OAuth 클라이언트 시크릿
# - GOOGLE_API_KEY: Google AI (Gemini) API 키
```

#### 암호화 키 생성

```bash
# Fernet 암호화 키 생성
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. 패키지 설치

```bash
# Python 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 3. 데이터베이스 마이그레이션

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations

# 마이그레이션 실행
python manage.py migrate

# 슈퍼유저 생성 (선택사항)
python manage.py createsuperuser
```

### 4. 개발 서버 실행

```bash
# 개발 서버 실행
python manage.py runserver

# 서버 접속
# - API: http://localhost:8000/api/v1/
# - Swagger: http://localhost:8000/api/v1/docs/
# - Admin: http://localhost:8000/admin/
```

## API 문서

Swagger UI: `http://localhost:8000/api/v1/docs/`

주요 엔드포인트:
- **인증**: `/api/v1/auth/`
- **사용자**: `/api/v1/users/`
- **메일**: `/api/v1/mails/`
- **폴더**: `/api/v1/folders/`
- **분류**: `/api/v1/classification/`

## 개발 가이드

### 모델 변경 시

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations

# 마이그레이션 실행
python manage.py migrate
```

### 테스트 실행

```bash
# 전체 테스트
pytest

# 특정 앱 테스트
pytest apps/accounts/tests/

# 커버리지와 함께 실행
pytest --cov=apps
```

### 코드 포맷팅

```bash
# Ruff로 린팅
ruff check .

# Ruff로 포맷팅
ruff format .
```

## 환경별 설정

### 개발 환경

```bash
export DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py runserver
```

### 운영 환경

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
gunicorn config.wsgi:application
```

## 데이터베이스 스키마

자세한 데이터베이스 스키마는 [DATABASE.md](../Pigeon-DOCS/docs/DATABASE.md)를 참조하세요.

주요 모델:
- **User**: Gmail OAuth2 인증 사용자 (토큰 암호화 저장)
- **Folder**: 메일 폴더 (최대 5단계 트리 구조)
- **Mail**: Gmail 메일 (분류 상태 포함)

## 보안

- OAuth2 토큰은 Fernet 대칭키 암호화로 DB에 저장
- JWT 토큰 기반 API 인증
- CORS 설정을 통한 출처 제한
- HTTPS 필수 (운영 환경)

## 라이선스

MIT License

## 관련 문서

- [API 명세서](../Pigeon-DOCS/docs/API_SPEC.md)
- [데이터베이스 설계](../Pigeon-DOCS/docs/DATABASE.md)
- [시스템 아키텍처](../Pigeon-DOCS/docs/ARCHITECTURE.md)
