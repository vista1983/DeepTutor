#!/bin/bash
set -euo pipefail
cd /app
python /app/deploy/render/bootstrap.py
exec /bin/bash /app/entrypoint.sh
