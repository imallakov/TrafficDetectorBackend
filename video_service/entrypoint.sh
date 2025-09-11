#!/bin/sh
set -e

# Run migrations including makemigrations for your app (replace 'core' with your app name if different)
python manage.py makemigrations

# Apply all migrations
python manage.py migrate

# Start Django development server (or replace with gunicorn command)
exec python manage.py runserver 0.0.0.0:8000
