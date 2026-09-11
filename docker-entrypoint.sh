#!/bin/bash
set -e

echo "Waiting for PostgreSQL database at $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "PostgreSQL is ready!"

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting container command: $@"
exec "$@"
