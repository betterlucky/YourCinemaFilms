#!/bin/bash
set -e

# Run collectstatic with --noinput flag to avoid interactive prompts
echo "Running collectstatic..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Start the application
echo "Starting application..."
exec "$@" 