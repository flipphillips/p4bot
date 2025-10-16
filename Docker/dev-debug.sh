#!/bin/bash
# Helper to run p4bot under debugpy inside the dev container
# Usage: run this inside the container (or via docker exec) to start gunicorn under debugpy
set -euo pipefail

# allow optional WAIT_FOR_CLIENT env var (default true)
WAIT_FOR_CLIENT=${WAIT_FOR_CLIENT:-true}

DBGFLAG=""
if [ "$WAIT_FOR_CLIENT" = "true" ]; then
  DBGFLAG="--wait-for-client"
fi

exec python -m debugpy --listen 0.0.0.0:5678 $DBGFLAG -m gunicorn -b 0.0.0.0:8080 --workers 1 --preload app.server:app
