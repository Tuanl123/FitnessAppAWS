#!/bin/sh
set -e

echo "Running user_db migrations..."
alembic upgrade head

exec "$@"
