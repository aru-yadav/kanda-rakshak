# Kanda Rakshak (कांदा रक्षक) — Smart Onion Storage Guard

A low-cost retrofit kit that turns a farmer's existing onion shed (kanda chawl) into a smart store.

- **Watches** heat, humidity and rot gas at three depths inside the onion heap
- **Acts** on its own: switches ventilation fans when outside air is drier, even with no network
- **Tells** the farmer one instruction a day in Marathi, on any phone: Hold, Sort or Sell, using the heap's rot risk plus the live mandi price from Govt data (Agmarknet via data.gov.in)

Built for the Seva First Innovation Challenge 2026 (Maharashtra), Sector 1 Agriculture, Sub-theme 5.

## Quick start

```bash
git clone git@github.com:<you>/kanda-rakshak.git && cd kanda-rakshak
./scripts/setup.sh                      # backend venv + deps + .env from example
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# new terminal
python tools/simulator.py --url http://localhost:8000 --scenario rot
# open http://localhost:8000
```

Hardware build: see `docs/hardware/HARDWARE.md` and `docs/hardware/wiring.svg`.
Full plan: `docs/PLAN.md`. Rules for Claude Code: `CLAUDE.md`.

## Architecture

```
 [DHT22 x4] [MQ-135] [MQ-136]
       \       |       /
        ESP32 (local fan rule, offline buffer)
           | WiFi (field: 4G/2G)
           v
 FastAPI backend --- data.gov.in mandi price (daily)
   | rot-risk | advisory (mr/en) | notifier (Telegram demo / SMS-IVR prod)
   v
 Dashboard (department / FPO view)
```

## Team
- Aryan Sunil Yadav — Team lead, software
- Sarvejeet More — Hardware lead

Department of CSE, MIT ADT University, Pune.

## Software demo (no hardware needed)
`./scripts/demo.sh` starts the backend plus a digital twin of 8 simulated sheds. Then open `/`, `/farmer` and `/dept`. Details and video script: `docs/SOFTWARE_DEMO.md`.

## Start with Claude Code
Read `docs/CLAUDE_CODE_PLAYBOOK.md`: exact prompts, session by session, from git init to submission.

`docs/dashboard-simulated-preview.png` shows the dashboard driven by the simulator (SIMULATED data, for layout reference only).
