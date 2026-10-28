#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 deploy/aliyun-shanghai/prepare.py
docker build --memory=600m -t deeptutor-shanghai:1.6.15-mcp -f deploy/render/Dockerfile .
docker run -d --name deeptutor-shanghai --restart unless-stopped \
  --env-file /opt/deeptutor/.env -e TZ=Asia/Shanghai -e PORT=10000 \
  --memory=850m --memory-swap=850m --cpus=1.5 --pids-limit=512 \
  --log-opt max-size=10m --log-opt max-file=3 \
  -p 127.0.0.1:3782:10000 -v /opt/deeptutor/data:/app/data \
  --health-cmd='curl -fsS http://127.0.0.1:10000/api/client-health || exit 1' \
  --health-start-period=180s --health-interval=30s --health-timeout=10s --health-retries=5 \
  deeptutor-shanghai:1.6.15-mcp
