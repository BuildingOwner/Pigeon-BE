@echo off
REM Pigeon Backend Setup Script for Windows

echo === Pigeon Backend Setup ===
echo.

REM 1. Check Python version
echo [1/7] Checking Python version...
python --version
echo.

REM 2. Install dependencies
echo [2/7] Installing dependencies...
pip install -r requirements.txt
echo.

REM 3. Generate Fernet key (if needed)
echo [3/7] Setting up .env file...
if not exist .env (
    copy .env.example .env
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    echo Please update TOKEN_ENCRYPTION_KEY in .env file with the key above
) else (
    echo .env file already exists
)
echo.

REM 4. Create migrations
echo [4/7] Creating migrations...
python manage.py makemigrations accounts
python manage.py makemigrations folders
python manage.py makemigrations mails
echo.

REM 5. Run migrations
echo [5/7] Running migrations...
python manage.py migrate
echo.

REM 6. Create superuser (optional)
echo [6/7] Create superuser? (skip for now)
REM python manage.py createsuperuser
echo.

REM 7. Done
echo [7/7] Setup complete!
echo.
echo Next steps:
echo   1. Update .env file with your Google OAuth credentials
echo   2. Update .env file with your Google API Key (Gemini)
echo   3. Run: python manage.py runserver
echo   4. Visit: http://localhost:8000/api/v1/docs/
echo.
pause
