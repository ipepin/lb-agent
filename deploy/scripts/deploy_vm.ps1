param(
  [string]$HostName = "136.109.34.192",
  [string]$User = "blaze",
  [string]$KeyPath = "$env:USERPROFILE\.ssh\google_compute_engine",
  [string]$RepoDir = "/opt/lb-agent",
  [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

$target = "$User@$HostName"
$remote = @"
set -euo pipefail
cd "$RepoDir"
mkdir -p deploy-backups
stamp=`$(date -u +%Y%m%dT%H%M%SZ)
git diff --binary > "deploy-backups/pre-deploy-`$stamp.patch" || true
tar --exclude='.venv' --exclude='deploy-backups' -czf "deploy-backups/pre-deploy-`$stamp-source.tgz" .
git fetch origin "$Branch"
git reset --hard "origin/$Branch"
"$RepoDir/.venv/bin/pip" install -r requirements.txt
sudo cp deploy/systemd/lb-agent-web.service /etc/systemd/system/lb-agent-web.service
sudo cp deploy/systemd/lb-agent-worker.service /etc/systemd/system/lb-agent-worker.service
sudo systemctl daemon-reload
sudo systemctl enable lb-agent-web >/dev/null
sudo systemctl enable lb-agent-worker >/dev/null
sudo systemctl restart lb-agent-web
sudo systemctl restart lb-agent-worker
sleep 3
systemctl is-active lb-agent-web
systemctl is-active lb-agent-worker
curl -fsS http://127.0.0.1:8000/api/health
"@

ssh -i $KeyPath -o BatchMode=yes $target $remote
