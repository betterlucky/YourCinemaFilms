#!/bin/bash

# Create superuser
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'pw7443') if not User.objects.filter(username='admin').exists() else print('Superuser already exists')" | python manage.py shell 