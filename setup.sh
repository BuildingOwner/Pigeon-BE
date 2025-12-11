#!/bin/bash
# Pigeon Backend Setup Script

echo "=== Pigeon Backend Setup ==="
echo ""

# 1. Check Python version
echo "[1/7] Checking Python version..."
python --version

# 2. Install dependencies
echo ""
echo "[2/7] Installing dependencies..."
pip install -r requirements.txt

# 3. Generate Fernet key (if needed)
echo ""
echo "[3/7] Generating encryption key..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    sed -i "s/TOKEN_ENCRYPTION_KEY=.*/TOKEN_ENCRYPTION_KEY=$KEY/" .env
    echo "✓ Generated new encryption key"
else
    echo "✓ .env file already exists"
fi

# 4. Create migrations
echo ""
echo "[4/7] Creating migrations..."
python manage.py makemigrations accounts
python manage.py makemigrations folders
python manage.py makemigrations mails

# 5. Run migrations
echo ""
echo "[5/7] Running migrations..."
python manage.py migrate

# 6. Create superuser (optional)
echo ""
echo "[6/7] Create superuser? (skip for now)"
# python manage.py createsuperuser

# 7. Done
echo ""
echo "[7/7] Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Update .env file with your Google OAuth credentials"
echo "  2. Update .env file with your Google API Key (Gemini)"
echo "  3. Run: python manage.py runserver"
echo "  4. Visit: http://localhost:8000/api/v1/docs/"
echo ""
