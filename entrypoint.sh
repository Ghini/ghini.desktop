#!/bin/sh
set -e

if [ -f /VERSION_ENV ]; then
    export $(cat /VERSION_ENV)
fi

DEBUG="${DEBUG:-false}"
APP_SCRIPT="${GHINI_APP_SCRIPT:-/app/scripts/ghini}"

echo "Entry point: DEBUG=$DEBUG"

if [ "$DEBUG" = "true" ]; then
    echo "Starting with debugpy..."
    exec python3 -m debugpy --wait-for-client --log-to /app/debugpy.log --listen 0.0.0.0:5678 "$APP_SCRIPT" "$@"
else
    echo "Starting normally..."
    exec python3 "$APP_SCRIPT" "$@"
fi
