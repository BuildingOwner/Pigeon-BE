# Pigeon Backend - Quick Start Guide

이 가이드는 Pigeon Backend를 빠르게 설정하고 실행하는 방법을 안내합니다.

## 사전 요구사항

- Python 3.10 이상
- pip (Python 패키지 관리자)

## 1단계: 의존성 설치

```bash
pip install -r requirements.txt
```

## 2단계: 환경 변수 설정

### 2-1. .env 파일 생성

`.env.example` 파일이 이미 있습니다. 이를 `.env`로 복사하거나 직접 편집하세요.

```bash
# Linux/macOS
cp .env.example .env

# Windows
copy .env.example .env
```

### 2-2. 암호화 키 생성

**중요**: `TOKEN_ENCRYPTION_KEY`를 반드시 설정해야 합니다.

```bash
# 다음 명령어로 새 키를 생성하세요
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

생성된 키를 `.env` 파일의 `TOKEN_ENCRYPTION_KEY` 값으로 설정하세요.

예:
```env
TOKEN_ENCRYPTION_KEY=U3VwZXJTZWNyZXRLZXlGb3JQaWdlb25EZXZlbG9wbWVudDIwMjU=
```

### 2-3. Google OAuth 설정 (선택사항)

실제 Gmail 연동을 테스트하려면 Google Cloud Console에서 OAuth 2.0 클라이언트를 생성하고 `.env`에 추가하세요:

```env
GOOGLE_CLIENT_ID=your-actual-client-id
GOOGLE_CLIENT_SECRET=your-actual-client-secret
GOOGLE_API_KEY=your-gemini-api-key
```

개발 단계에서는 기본값을 그대로 두어도 됩니다.

## 3단계: 데이터베이스 마이그레이션

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations

# 마이그레이션 실행
python manage.py migrate
```

**예상 출력:**
```
Operations to perform:
  Apply all migrations: accounts, admin, auth, contenttypes, folders, mails, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying accounts.0001_initial... OK
  Applying folders.0001_initial... OK
  Applying mails.0001_initial... OK
  ...
```

## 4단계: 개발 서버 실행

```bash
python manage.py runserver
```

서버가 실행되면 다음 URL에 접속할 수 있습니다:

- **API 루트**: http://localhost:8000/api/v1/
- **Swagger UI**: http://localhost:8000/api/v1/docs/
- **Django Admin**: http://localhost:8000/admin/

## 5단계: Swagger UI 확인

브라우저에서 http://localhost:8000/api/v1/docs/ 에 접속하여 API 문서를 확인하세요.

다음 엔드포인트들이 표시되어야 합니다:

- `/api/v1/auth/` - 인증 관련
- `/api/v1/folders/` - 폴더 관리
- `/api/v1/mails/` - 메일 관리
- `/api/v1/classification/` - AI 분류

## 문제 해결

### "TOKEN_ENCRYPTION_KEY environment variable is not set" 에러

`.env` 파일의 `TOKEN_ENCRYPTION_KEY`를 확인하세요. 2-2 단계를 참조하여 유효한 키를 생성하세요.

### "No such file or directory: 'db.sqlite3'"

마이그레이션을 먼저 실행하세요 (3단계).

### "ModuleNotFoundError"

의존성 설치를 확인하세요 (1단계).

```bash
pip install -r requirements.txt
```

## 자동 설치 스크립트

위 단계를 자동으로 실행하려면:

```bash
# Linux/macOS
chmod +x setup.sh
./setup.sh

# Windows
setup.bat
```

## 다음 단계

1. **슈퍼유저 생성** (선택사항):
   ```bash
   python manage.py createsuperuser
   ```

2. **테스트 실행**:
   ```bash
   pytest
   ```

3. **API 문서 확인**: http://localhost:8000/api/v1/docs/

## 참고 문서

- [README.md](./README.md) - 전체 문서
- [DATABASE.md](../Pigeon-DOCS/docs/DATABASE.md) - 데이터베이스 설계
- [API_SPEC.md](../Pigeon-DOCS/docs/API_SPEC.md) - API 명세서
