#!/usr/bin/env bash
# One-shot local setup (Mac/Linux). Windows: run the same steps in Git Bash or WSL.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv backend/.venv
backend/.venv/bin/pip install -q -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -f firmware/include/secrets.h ] || cp firmware/include/secrets.example.h firmware/include/secrets.h
mkdir -p data && touch data/.gitkeep
echo "Done. Edit backend/.env and firmware/include/secrets.h, then:"
echo "  cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
