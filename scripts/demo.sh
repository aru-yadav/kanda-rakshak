#!/usr/bin/env bash
# Start the full software demo: backend + digital twin (8 simulated sheds).
# Mac/Linux. Stop with Ctrl+C (stops both).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d backend/.venv ] || ./scripts/setup.sh
source backend/.venv/bin/activate
TOKEN=$(grep -E '^DEVICE_TOKEN=' backend/.env | cut -d= -f2-)
# localhost only: with DEMO_MODE on, anyone who can reach the server could drive the simulated sheds
( cd backend && DEMO_MODE=true uvicorn app.main:app --host 127.0.0.1 --port 8000 ) &
API=$!
trap 'kill $API 2>/dev/null' EXIT
sleep 3
echo ""
echo "  Shed dashboard : http://localhost:8000/?device=SIM-NSK-01"
echo "  Farmer app     : http://localhost:8000/farmer?device=SIM-NSK-01"
echo "  Department     : http://localhost:8000/dept"
echo ""
python tools/digital_twin.py --url http://localhost:8000 --token "$TOKEN" --interval 2 --minutes 30
