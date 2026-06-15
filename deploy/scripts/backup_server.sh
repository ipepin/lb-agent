#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:-/opt/lb-agent}"
backup_dir="$repo_dir/deploy-backups"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$backup_dir"
cd "$repo_dir"

if [ -f "data/app.db" ]; then
  cp "data/app.db" "$backup_dir/app-$stamp.db"
fi

tar --exclude='.venv' --exclude='deploy-backups' -czf "$backup_dir/data-$stamp.tgz" data
find "$backup_dir" -type f -mtime +30 -delete

echo "$backup_dir/data-$stamp.tgz"
