#!/usr/bin/env bash
# One-shot local setup (Mac/Linux). Windows: run the same steps in Git Bash or WSL.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv backend/.venv
backend/.venv/bin/pip install -q -r backend/requirements.txt
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  # fresh random tokens: the backend refuses to start with empty/default ones
  DT=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))'); AT=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')
  sed -i.bak -e "s|^DEVICE_TOKEN=.*|DEVICE_TOKEN=$DT|" -e "s|^ADMIN_TOKEN=.*|ADMIN_TOKEN=$AT|" backend/.env && rm -f backend/.env.bak
  echo "Generated DEVICE_TOKEN/ADMIN_TOKEN in backend/.env. Put the same DEVICE_TOKEN in firmware/include/secrets.h."
fi
[ -f firmware/include/secrets.h ] || cp firmware/include/secrets.example.h firmware/include/secrets.h
mkdir -p data && touch data/.gitkeep
echo "Done. Edit backend/.env and firmware/include/secrets.h, then:"
echo "  cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "  (0.0.0.0 is needed for a real ESP32 on WiFi; use --host 127.0.0.1 when no device must reach it)"
