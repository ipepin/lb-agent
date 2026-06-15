# Google Cloud Deploy

Produkcni VM pro LB-AGENT pouziva repo primo v `/opt/lb-agent`.

```text
/opt/lb-agent/
|-- app/                 # Python package
|-- data/                # SQLite, tokeny, prilohy
|-- deploy/
|-- .venv/               # Python virtualenv
|-- .env                 # produkcni env
`-- credentials.json
```

Starsi varianta s `/opt/lb-agent/app` jako clone adresar se uz nepouziva.

## Bootstrap

```bash
sudo mkdir -p /opt/lb-agent
sudo chown -R $USER:$USER /opt/lb-agent
git clone <REPO_URL> /opt/lb-agent
cd /opt/lb-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p data/attachments
cp .env.example .env
```

## Systemd

```bash
cd /opt/lb-agent
sudo cp deploy/systemd/lb-agent-web.service /etc/systemd/system/
sudo cp deploy/systemd/lb-agent-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lb-agent-web
sudo systemctl enable --now lb-agent-worker
```

Kontrola:

```bash
systemctl status lb-agent-web
systemctl status lb-agent-worker
journalctl -u lb-agent-web -n 100 --no-pager
journalctl -u lb-agent-worker -n 100 --no-pager
```

## Nginx a HTTPS

```bash
sudo cp deploy/nginx/lb-agent.conf /etc/nginx/sites-available/lb-agent
sudo ln -sfn /etc/nginx/sites-available/lb-agent /etc/nginx/sites-enabled/lb-agent
sudo nginx -t
sudo systemctl reload nginx
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <DOMENA>
```

## Aktualizace z Windows

```powershell
.\deploy\scripts\deploy_vm.ps1
```

## Rucni aktualizace na serveru

```bash
cd /opt/lb-agent
bash deploy/scripts/backup_server.sh
git fetch origin main
git reset --hard origin/main
/opt/lb-agent/.venv/bin/pip install -r requirements.txt
sudo cp deploy/systemd/lb-agent-web.service /etc/systemd/system/
sudo cp deploy/systemd/lb-agent-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart lb-agent-web
sudo systemctl restart lb-agent-worker
curl -fsS http://127.0.0.1:8000/api/health
```

## Zaloha dat

```bash
bash deploy/scripts/backup_server.sh
```

Skript ulozi kopii SQLite databaze a archiv slozky `data/` do `deploy-backups/` a smaze zalohy starsi nez 30 dni.
