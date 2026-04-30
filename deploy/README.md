# Google Cloud Deploy

Tato složka připravuje `LB-AGENT` na nasazení na jednu `Google Cloud Compute Engine` VM.

Doporučený základ:
- `Ubuntu 24.04 LTS`
- `e2-micro`
- veřejná IP
- otevřené porty `80` a `443`

## Cílové rozložení

Na serveru:

```text
/opt/lb-agent/
├── app/                 # git clone projektu
├── .venv/               # python virtualenv
├── shared/
│   ├── .env            # produkční env
│   ├── credentials.json
│   └── data/
│       ├── app.db
│       ├── attachments/
│       ├── gmail_token.json
│       ├── google_calendar_token.json
│       └── last_sync.txt
└── logs/
```

Lokální projekt počítá s `data/` a `.env` v kořeni repo. Na serveru to vyřeší symlinky:
- `/opt/lb-agent/app/.env -> /opt/lb-agent/shared/.env`
- `/opt/lb-agent/app/data -> /opt/lb-agent/shared/data`
- `/opt/lb-agent/app/credentials.json -> /opt/lb-agent/shared/credentials.json`

## 1. Připojení na VM

Použij SSH z Google Cloud konzole nebo lokálně:

```bash
gcloud compute ssh <VM_NAME> --zone <ZONE>
```

## 2. Bootstrap serveru

Nahraj repo nebo ho naklonuj a pak spusť:

```bash
sudo bash deploy/scripts/bootstrap_ubuntu.sh
```

Skript:
- nainstaluje systémové balíčky
- vytvoří adresáře v `/opt/lb-agent`
- připraví virtualenv
- nainstaluje Python závislosti

## 3. Nasazení aplikace

Pokud už je repo na serveru:

```bash
sudo mkdir -p /opt/lb-agent
sudo chown -R $USER:$USER /opt/lb-agent
git clone <TVE_REPO_URL> /opt/lb-agent/app
cd /opt/lb-agent/app
```

Vytvoř sdílené soubory:

```bash
mkdir -p /opt/lb-agent/shared/data/attachments
cp .env.example /opt/lb-agent/shared/.env
cp credentials.json /opt/lb-agent/shared/credentials.json
```

Pak nastav symlinky:

```bash
ln -sfn /opt/lb-agent/shared/.env /opt/lb-agent/app/.env
ln -sfn /opt/lb-agent/shared/data /opt/lb-agent/app/data
ln -sfn /opt/lb-agent/shared/credentials.json /opt/lb-agent/app/credentials.json
```

## 4. Systemd služby

Zkopíruj service soubory:

```bash
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

## 5. Nginx

Zkopíruj konfiguraci:

```bash
sudo cp deploy/nginx/lb-agent.conf /etc/nginx/sites-available/lb-agent
sudo ln -sfn /etc/nginx/sites-available/lb-agent /etc/nginx/sites-enabled/lb-agent
sudo nginx -t
sudo systemctl reload nginx
```

## 6. HTTPS

Po nastavení domény:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <TVA_DOMENA>
```

## 7. Důležité produkční poznámky

- `GOOGLE_CALENDAR_ID` a OAuth tokeny musí být na serveru ve sdílené složce.
- Po prvním deployi znovu ověř:
  - Gmail sync
  - zápis do Google Kalendáře
  - přílohy
- SQLite teď stačí. Až bude víc uživatelů naráz, přejdeme na PostgreSQL.

## 8. Aktualizace aplikace

```bash
cd /opt/lb-agent/app
git pull
/opt/lb-agent/.venv/bin/pip install -r requirements.txt
sudo systemctl restart lb-agent-web
sudo systemctl restart lb-agent-worker
```
