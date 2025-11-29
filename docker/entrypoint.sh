#!/bin/bash
set -e

echo "🚀 Starting Recruitment Platform Services..."

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "⏳ Waiting for PostgreSQL to be ready..."
    until pg_isready -h "$DB_HOST" -U "$DB_USER"; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done
    echo "✅ PostgreSQL is ready!"
}

# Function to run Django migrations
run_migrations() {
    echo "🔄 Running Django migrations..."
    python manage.py migrate --noinput
    echo "✅ Migrations complete!"
}

# Function to collect static files
collect_static() {
    echo "📦 Collecting static files..."
    python manage.py collectstatic --noinput || true
    echo "✅ Static files collected!"
}

# Function to create superuser if needed
create_superuser() {
    echo "👤 Checking for superuser..."
    python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️  Superuser already exists')
EOF
}

# Main execution
if [ "$1" = "django" ]; then
    echo "🐍 Starting Django Backend..."
    wait_for_postgres
    run_migrations
    collect_static
    create_superuser
    
    echo "🌐 Starting Daphne ASGI server (WebSocket support)..."
    exec daphne -b 0.0.0.0 -p 8001 recruitment_backend.asgi:application

elif [ "$1" = "fastapi" ]; then
    echo "⚡ Starting FastAPI Service..."
    exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

else
    echo "❌ Unknown service: $1"
    echo "Usage: entrypoint.sh [django|fastapi]"
    exit 1
fi
