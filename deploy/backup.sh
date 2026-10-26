#!/usr/bin/env bash
# Ежедневный бэкап БД и медиа. Cron: 0 3 * * * /opt/bloknot/deploy/backup.sh >> /var/log/bloknot-backup.log 2>&1
# ВАЖНО: копируйте каталог backups/ на другой сервер/в облако (rclone, rsync, S3) — копия на том же диске не защищает от потери сервера.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p backups
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-bloknot}" -Fc "${POSTGRES_DB:-bloknot}" > "backups/db-$STAMP.dump"
docker compose exec -T backend tar -C /app -cf - media > "backups/media-$STAMP.tar"
find backups -type f -mtime +14 -delete
echo "backup ok: $STAMP"
