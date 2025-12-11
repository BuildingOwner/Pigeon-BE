# Pigeon Backend - Setup Checklist

## Phase 1 개발 완료 체크리스트

### ✅ Issue #4: Django 프로젝트 초기화

- [x] Django 프로젝트 생성 (config/)
- [x] settings 분리
  - [x] config/settings/base.py (공통 설정)
  - [x] config/settings/development.py (개발 환경)
  - [x] config/settings/production.py (운영 환경)
- [x] requirements.txt 작성
  - [x] Django 5.0
  - [x] DRF
  - [x] drf-spectacular
  - [x] django-cors-headers
  - [x] simplejwt
  - [x] google-auth
  - [x] langchain
  - [x] cryptography
- [x] .env.example 생성
- [x] .gitignore 업데이트

### ✅ Issue #5: Django 앱 생성 및 설정

- [x] 앱 생성
  - [x] accounts (사용자 인증)
  - [x] folders (폴더 관리)
  - [x] mails (메일 관리)
  - [x] classifier (AI 분류)
- [x] DRF 설정
  - [x] REST_FRAMEWORK 설정 (base.py)
  - [x] JWT 인증 설정
  - [x] 페이지네이션 설정
- [x] drf-spectacular (Swagger) 설정
  - [x] SPECTACULAR_SETTINGS 설정
  - [x] /api/v1/docs/ URL 설정
- [x] CORS 설정
  - [x] corsheaders 미들웨어 추가
  - [x] CORS_ALLOWED_ORIGINS 설정
- [x] JWT 설정
  - [x] SIMPLE_JWT 설정
  - [x] Access Token: 1시간
  - [x] Refresh Token: 7일
- [x] URL 라우팅 설정
  - [x] /api/v1/auth/ (accounts)
  - [x] /api/v1/folders/ (folders)
  - [x] /api/v1/mails/ (mails)
  - [x] /api/v1/classification/ (classifier)

### ✅ Issue #6: DB 모델 정의

- [x] User 모델 (apps/accounts/models.py)
  - [x] AbstractUser 상속
  - [x] email (unique)
  - [x] gmail_access_token (암호화)
  - [x] gmail_refresh_token (암호화)
  - [x] gmail_token_expires_at
  - [x] gmail_history_id (증분 동기화용)
  - [x] name, picture (프로필)
  - [x] last_sync_at, is_initial_sync_done
  - [x] Fernet 암호화/복호화 property

- [x] Folder 모델 (apps/folders/models.py)
  - [x] user (FK)
  - [x] parent (자기참조 FK)
  - [x] name, path, depth
  - [x] mail_count, unread_count (캐시)
  - [x] order (정렬)
  - [x] UniqueConstraint(user, path)
  - [x] save() 메서드에서 자동 depth/path 계산

- [x] Mail 모델 (apps/mails/models.py)
  - [x] user (FK)
  - [x] folder (FK, nullable)
  - [x] gmail_id, thread_id
  - [x] subject, sender, sender_email
  - [x] recipients (JSONField)
  - [x] snippet, body_html
  - [x] attachments (JSONField)
  - [x] has_attachments
  - [x] is_classified, is_read, is_starred, is_deleted
  - [x] received_at
  - [x] UniqueConstraint(user, gmail_id)
  - [x] 인덱스 설정

### 📋 추가 작업 완료

- [x] core 모듈
  - [x] exceptions.py (커스텀 예외)
  - [x] pagination.py (페이지네이션)
  - [x] permissions.py (권한 클래스)
- [x] 문서화
  - [x] README.md 업데이트
  - [x] QUICK_START.md 작성
  - [x] setup.sh / setup.bat 스크립트
- [x] .env 파일 설정
  - [x] TOKEN_ENCRYPTION_KEY 추가

## 🚀 실행 전 필수 작업

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일의 `TOKEN_ENCRYPTION_KEY`를 유효한 Fernet 키로 변경:

```bash
# 실제 Fernet 키 생성
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 생성된 키를 .env 파일에 복사
# TOKEN_ENCRYPTION_KEY=<생성된_키>
```

### 3. 마이그레이션 실행

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations

# 마이그레이션 실행
python manage.py migrate
```

### 4. 개발 서버 실행

```bash
python manage.py runserver
```

### 5. Swagger UI 접속

http://localhost:8000/api/v1/docs/

## 📝 DoD (Definition of Done) 체크리스트

아래 항목들을 모두 확인해야 합니다:

- [ ] `python manage.py runserver` 정상 실행
- [ ] http://localhost:8000/api/v1/docs/ Swagger UI 접속 가능
- [ ] Swagger UI에 다음 엔드포인트 표시:
  - [ ] /api/v1/auth/
  - [ ] /api/v1/folders/
  - [ ] /api/v1/mails/
  - [ ] /api/v1/classification/
- [ ] 마이그레이션 완료 (db.sqlite3 파일 생성됨)
- [ ] 린트 에러 없음

### 린트 체크 (선택사항)

```bash
# Ruff 설치 (아직 안 했다면)
pip install ruff

# 린트 검사
ruff check .

# 포맷팅
ruff format .
```

## 🎯 다음 단계 (Phase 2)

Phase 1 완료 후:

1. Gmail OAuth 서비스 구현
2. Gmail 동기화 서비스 구현
3. LLM 분류 서비스 구현
4. 테스트 코드 작성

---

**참고**: 이 문서는 Phase 1 개발 완료를 위한 체크리스트입니다.
