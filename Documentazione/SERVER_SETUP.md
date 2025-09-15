# Windows Server Setup Guide (Staging/Client Test)

This guide walks you through deploying the WhatsApp OpenAI Bot on Windows Server (2019/2022) or Windows 10/11 for 24/7 uptime using:
- Python virtualenv
- Waitress (production WSGI server)
- ngrok (public HTTPS webhook)
- Task Scheduler to auto‑start the bot (and optionally ngrok)

## 1) Prerequisites
- Admin access to the Windows machine (RDP/console)
- WhatsApp Business credentials:
  - `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_ID`, `VERIFY_TOKEN`, `META_APP_SECRET`
- OpenAI credentials: `OPENAI_API_KEY`, `OPENAI_PROMPT_ID`, optional `OPENAI_MODEL`
- ngrok account + authtoken (preferably with a reserved domain)

## 2) Install Required Tools
1) Python 3.10+ for Windows
- Download from https://www.python.org/downloads/windows/
- Check “Add Python to PATH” during install.

2) Git for Windows (optional, or download the repo ZIP)
- https://git-scm.com/download/win

3) ngrok
- Install via Winget (recommended):
  - Open PowerShell as Administrator: `winget install --id Ngrok.Ngrok -e`
  - Or download MSI from https://ngrok.com/download

4) Optional: allow local scripts
- Ensure PowerShell can run your local wrapper script:
  - `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force`

## 3) Create Folders and Clone the Repo (Documents Path)
Open PowerShell (as your admin user). We’ll place the project under your Documents (no OneDrive required):
```powershell
$base = Join-Path $env:USERPROFILE 'Documents\whatsapp-bot'
New-Item -ItemType Directory -Force -Path (Join-Path $base 'app') | Out-Null
Set-Location (Join-Path $base 'app')

# Clone normally (creates a nested folder like .\whatsapp_test01)
git clone <YOUR_REPO_URL>

# Set a repo variable (adjust the folder name if different)
$repo = Join-Path (Join-Path $base 'app') 'whatsapp_test01'
if (-not (Test-Path $repo)) { Write-Host 'Update $repo to your actual folder name.' -ForegroundColor Yellow }
```

## 4) Create Virtual Environment and Install Deps
Create venv in `app\.venv`, then install deps from inside the repo folder.
```powershell
# Create venv (sibling of the repo folder)
python -m venv (Join-Path (Join-Path $base 'app') '.venv')

# Activate venv
& (Join-Path (Join-Path $base 'app') '.venv\Scripts\Activate.ps1')

# Install requirements from inside the repo folder
Set-Location $repo
if (-not (Test-Path .\requirements.txt)) { Write-Error "requirements.txt not found in $repo. Check the path." }
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install waitress

# Allow running local scripts if blocked
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
```

## 5) Configure Environment (.env)
Create `$repo\.env` with:
```ini
ENVIRONMENT=production
PORT=3000
VERIFY_TOKEN=REPLACE_WITH_STRONG_TOKEN

# WhatsApp Business
WHATSAPP_ACCESS_TOKEN=REPLACE
WHATSAPP_PHONE_ID=REPLACE
META_APP_SECRET=REPLACE

# OpenAI
OPENAI_API_KEY=REPLACE
OPENAI_PROMPT_ID=REPLACE
OPENAI_MODEL=gpt-4.1

# Optional logging
LOG_LEVEL=INFO
```

Note: The application reads environment variables at process start. We’ll use a wrapper script to load `.env` before launching the server.



Set-Location $repo



## 7) Install and Configure ngrok. SEE NGROK GUIDE FOR THIS
Login and set authtoken:
```powershell
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
```
THIS IS OUTDATED, SEE GUIDE
Create ngrok config at `$env:LOCALAPPDATA\ngrok\ngrok.yml` (default location used by ngrok service):
se non trovi il config file, run: ngrok config edit
```yaml
version: 2
region: eu
authtoken: <YOUR_NGROK_AUTHTOKEN>
log: stdout
tunnels:
  whatsapp-bot:
    proto: http
    addr: 127.0.0.1:3000
    schemes: [https]
    # domain: your-reserved-subdomain.eu.ngrok.io   # optional reserved domain
```


## 8) Auto‑Start at Boot (Task Scheduler + ngrok service)
we will use ALWAYSUP

- Program/script: ` C:\Users\Administrator\Documents\whatsapp-bot\app\.venv\Scripts\python.exe`
- Add arguments: start_openai_bot.py`
- Start in: `C:\Users\Administrator\Documents\whatsapp-bot\app\whatsapp_test01`


cambia  app.run(debug=True) to false nello script quando andiamo in produzione


## 9) Configure WhatsApp Webhook
Usa dominio scelto e passowrd su whatsapp, una volta sola.

## 10) Data and Backups
- SQLite DB path (default): `$repo\whatsapp_bot.db` (the app writes relative to its working directory)
- Quick backup (Task Scheduler setup):
```powershell
Stop-ScheduledTask -TaskName 'WA-Bot' -ErrorAction SilentlyContinue
Copy-Item (Join-Path $repo 'whatsapp_bot.db') (Join-Path $base ("backup-" + (Get-Date -Format yyyy-MM-dd) + ".db"))
Start-ScheduledTask -TaskName 'WA-Bot'
```

## 11) Updating the App
```powershell
Stop-ScheduledTask -TaskName 'WA-Bot' -ErrorAction SilentlyContinue
Set-Location $repo
git pull --rebase    # or replace files if using ZIP
& (Join-Path (Join-Path $base 'app') '.venv\Scripts\Activate.ps1')
pip install -r requirements.txt
pip install waitress
Start-ScheduledTask -TaskName 'WA-Bot'
```

## 12) Verification Checklist
- WA-Bot Task Scheduler task runs successfully and logs show “healthy”.
- ngrok is running (via ngrok service or Task Scheduler) and shows a public HTTPS URL.
- `GET /health` returns JSON via the public URL.
- WhatsApp webhook verification succeeds and messages reach the bot.

## 13) Security Notes (Important)
- Waitress binds to `127.0.0.1:3000` only. Do not expose it directly.
- Use a strong `VERIFY_TOKEN` and set `META_APP_SECRET` to validate webhook signatures (ensure code support is enabled later).
- Keep `.env` readable only by admins; avoid sharing logs that include PII.
- If/when dashboard auth is added, protect `/dashboard` and all `/api/*` and include CSRF for POSTs.

## 14) Optional: Node Webhook Logger via Task Scheduler
If you use `app.js` for logging (optional), create a Task Scheduler entry similar to WA‑Bot:

- Program/script: `node`
- Add arguments: `app.js`
- Start in: your repo folder (`$repo`)
- Triggers: At startup; restart on failure

Note: If exposing this publicly, implement webhook signature verification in Node too.

---

You’re done. The bot runs 24/7 via Task Scheduler, with ngrok providing a public HTTPS webhook URL for WhatsApp testing.
