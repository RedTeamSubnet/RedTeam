#!/bin/bash
# Exit on any error
set -e

# Define variables
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-10002}"

# Start the server
echo "Starting uvicorn server on ${HOST}:${PORT}"
cd src || exit 1
uvicorn app:app \
   --host="$HOST" \
   --port="$PORT" \
   --no-access-log \
   --no-server-header \
   --proxy-headers \
   --forwarded-allow-ips="*"
