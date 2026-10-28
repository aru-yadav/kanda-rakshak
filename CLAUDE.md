# CLAUDE.md — Kanda Rakshak (कांदा रक्षक)

Read this file fully before any work. It is the contract for every Claude Code session in this repo.

## 1. What we are building

A retrofit kit for an existing onion storage shed (kanda chawl). It measures heat, humidity and rot gas inside the heap, runs ventilation fans automatically, and sends the farmer one daily instruction in Marathi (Hold / Sort / Sell) by combining the heap's rot risk with the live mandi price.

Competition: Seva First Innovation Challenge 2026, Maharashtra zone, Sector 1 (Agriculture), Sub-theme 5 (Post-Harvest Loss, Storage and Price Protection for Crops).
Hard deadline: final PPT and demo submission **30 Oct 2026**. Internal deadline: **29 Oct 2026, 20:00 IST**.
Team: Aryan Sunil Yadav (team lead, software), Sarvejeet More (hardware lead).

## 2. The one rule

**One loop working end to end beats five features half-working.**
The demo loop is:

```
onion box -> ESP32 sensors -> backend -> rot-risk score + real mandi price -> advice
          -> fan switches automatically (on the device itself)
          -> Marathi text + voice message on a phone
          -> dashboard shows all of it live
```

Anything not on that loop is out of scope until the loop is green (see docs/PLAN.md, Gate G3).

## 3. Repo map

| Path | What lives there | Owner |
|---|---|---|
| `firmware/` | PlatformIO project for ESP32 (C++/Arduino) | Sarvejeet |
| `backend/` | FastAPI + SQLite service, rot-risk, price, advisory, notifier | Aryan |
| `dashboard/` | Single-page HTML + Chart.js, served by the backend | Aryan |
| `tools/simulator.py` | Fake device for building software before hardware arrives | Aryan |
| `docs/` | Plan, tech stack, hardware wiring, test protocol, demo script, risks | both |
| `.claude/agents/` | Sub-agents (red team, blue team, reviewers) | both |
| `.claude/commands/` | Slash commands (/gate, /redteam, /standup, /jury) | both |

## 4. Working rules for Claude Code

1. **Plan before code.** For any task larger than one file, write the plan in the chat first, list files to touch, then implement.
2. **Four-eyes.** Every PR touching `firmware/` gets `hardware-safety-reviewer`; every PR gets `red-team` before merge. Blue team fixes; red team re-checks. Nothing merges to `main` with an open CRITICAL finding.
3. **Tests or it didn't happen.** Backend logic (`rotrisk.py`, `advisory.py`, `price.py`) must have pytest coverage for every rule. Run `pytest -q` before every commit.
4. **Firmware must compile.** Run `pio run` in `firmware/` before every commit that touches it.
5. **No fake data in the demo.** Simulated data is only allowed from device IDs starting with `SIM-` and the dashboard must label it "SIMULATED". The `data-integrity-auditor` agent enforces this. A juror who catches one fake graph will discard the whole entry.
6. **No secrets in git.** WiFi passwords, API keys, bot tokens live in `firmware/include/secrets.h` and `backend/.env`, both gitignored. Only `*.example` files are committed.
7. **Small commits, conventional messages.** `feat(firmware): ...`, `fix(backend): ...`, `docs: ...`, `test: ...`.
8. **Do not add dependencies casually.** Any new library needs a one-line justification in the PR and must be in docs/TECH_STACK.md.
9. **When unsure about hardware, stop and ask.** Wrong wiring can kill an ESP32 or start a fire with 12V. Never guess a pin.
10. **Every number shown to a juror needs a source** (sensor log, API response, or a cited document). Keep `docs/EVIDENCE.md` updated.

## 5. Commands

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill keys
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pytest -q

# simulator (no hardware needed)
python tools/simulator.py --url http://localhost:8000 --scenario rot

# firmware
cd firmware && cp include/secrets.example.h include/secrets.h   # fill WiFi + server IP
pio run && pio run -t upload && pio device monitor
```

## 6. Definition of done for the demo (Gate G5)

- [ ] Real ESP32 posting real readings from a real onion box for 48 h
- [ ] Fan switches on/off by itself with the network unplugged (offline proof)
- [ ] Real Lasalgaon (or nearest) onion modal price pulled from data.gov.in, with date shown
- [ ] Rot box vs fresh box graph from our own log, unedited
- [ ] Marathi text + voice message received on a phone during filming
- [ ] Dashboard shows device, layers, fan state, risk, price, advice
- [ ] 2–3 min video uploaded (unlisted), link in deck
- [ ] Deck updated: stage = Working Prototype, prototype photo, real graph


## Company policy
Also follow docs/PROJECT_INSTRUCTIONS.md. If it conflicts with this file, the stricter rule wins.
