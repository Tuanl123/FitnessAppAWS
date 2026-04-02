#!/bin/sh
set -e

echo "Running analytics_db migrations..."
alembic upgrade head

exec "$@"
