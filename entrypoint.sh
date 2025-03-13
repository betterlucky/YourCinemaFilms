#!/bin/bash

# Start Nginx
nginx -g "daemon off;" & # & runs nginx in the background

# Create db directory if it doesn't exist
mkdir -p /app/db

# Create an empty database file if it doesn't exist
if [ ! -f /app/db/db.sqlite3 ]; then
    touch /app/db/db.sqlite3
fi

# Ensure proper permissions for database
chmod -R 777 /app/db
chmod 666 /app/db/db.sqlite3

# Create staticfiles directory with proper permissions
echo "Setting up static files directory..."
rm -rf /app/staticfiles
mkdir -p /app/staticfiles
mkdir -p /app/staticfiles/css
mkdir -p /app/staticfiles/js
mkdir -p /app/staticfiles/img
mkdir -p /app/staticfiles/admin
mkdir -p /app/staticfiles/admin/css
mkdir -p /app/staticfiles/admin/js
mkdir -p /app/staticfiles/admin/img
mkdir -p /app/staticfiles/rest_framework
chmod -R 777 /app/staticfiles
ls -la /app/staticfiles

# Debug information
echo "Database directory permissions:"
ls -la /app/db/

# Make migrations first to ensure they're up to date
echo "Creating migrations..."
python manage.py makemigrations

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static
echo "Collecting static..."
PYTHONUNBUFFERED=1 python manage.py collectstatic --noinput --clear

# Don't try to copy to nginx container - we're using tmpfs in both containers
echo "Static files collected successfully"

# Create superuser using Django shell
echo "Creating superuser..."
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'pw7443') if not User.objects.filter(username='admin').exists() else print('Superuser already exists')" | python manage.py shell

echo "Run google Oauth update"
python setup_google_oauth.py

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8080 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    films_project.wsgi:application