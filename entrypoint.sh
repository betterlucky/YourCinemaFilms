#!/bin/bash

# Start Nginx with the custom configuration
nginx -c /etc/nginx/nginx.conf -g "daemon off;" &

# Create db directory if it doesn't exist
mkdir -p /app/db

# Create an empty database file if it doesn't exist
if [ ! -f /app/db/db.sqlite3 ]; then
    touch /app/db/db.sqlite3
fi

# Ensure proper permissions
chmod -R 777 /app/db
chmod 666 /app/db/db.sqlite3

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
python manage.py collectstatic --noinput

# Create superuser using Django shell
echo "Creating superuser..."
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'pw7443') if not User.objects.filter(username='admin').exists() else print('Superuser already exists')" | python manage.py shell

# Run Google OAuth setup
echo "Run google Oauth update"
python manage.py setup_google_oauth

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8080 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    films_project.wsgi:application
