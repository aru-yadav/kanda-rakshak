# Kanda Rakshak (कांदा रक्षक): Smart Onion Storage Guard

**Seva First Innovation Challenge 2026 (Maharashtra)** · Sector 1 Agriculture · Sub-theme 5: Post-Harvest Loss, Storage and Price Protection

A low-cost (≈₹7,900, BOM in progress) retrofit kit that turns a farmer's existing onion shed (kanda chawl) into a smart store:

- **Watches** heat, humidity and rot gas at the top, middle and bottom of the onion heap
- **Acts** on its own: switches ventilation fans on when outside air is drier, even with no network
- **Tells** the farmer one instruction a day in Marathi: **Hold, Sort or Sell**. Demo channel: Telegram text + voice note. Planned: SMS / voice call for keypad phones. The instruction combines the heap's rot risk with the live mandi price from Government Agmarknet data (data.gov.in).

> Demo video: `<paste YouTube link>`

## Status (honest)

| Part | Status |
|---|---|
| Backend (FastAPI), rule-based rot-risk score, Marathi advisory, `/explain` decision trace | ✅ Built, 67 automated tests passing |
| Live mandi price (data.gov.in Agmarknet) | ✅ Integrated, with cache and fallback labels |
| Farmer app, shed dashboard, department/FPO dashboard | ✅ Built |
| Digital twin: 8 simulated sheds around Nashik | ✅ Running. Heap model with assumed coefficients; fan rule modelled on the firmware (not yet verified against it) |
| SMS / voice call for keypad phones | 📅 Planned (demo uses Telegram) |
| ESP32 firmware + hardware (DHT22 ×4, MQ-135/136, solar fan) | 🔧 Firmware written (compile pending), hardware being assembled |
| Field pilot (80 sheds, Niphad–Lasalgaon) | 📅 Proposed |

All demo data comes from the digital twin and is labelled **SIMULATED** in the UI. Twin results (e.g. kit ON vs OFF) come from a model with assumed numbers, not from measurements.

Screenshots are being retaken after the price-labelling fix (the earlier ones showed a fallback price as "today's rate").

## Run the demo (no hardware needed)

```bash
git clone https://github.com/<you>/kanda-rakshak.git && cd kanda-rakshak
./scripts/setup.sh      # Python venv, dependencies, .env from example
./scripts/demo.sh       # backend + digital twin of 8 sheds
```

Then open:
- http://localhost:8000/ for the shed view
- http://localhost:8000/farmer for the farmer phone view
- http://localhost:8000/dept for the department view

Run the tests with `cd backend && source .venv/bin/activate && pytest`.

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
 Farmer app · Shed dashboard · Department / FPO dashboard
```

- Hardware build: `docs/hardware/HARDWARE.md`, wiring in `docs/hardware/wiring.svg`
- Full plan: `docs/PLAN.md`
- Software demo details: `docs/SOFTWARE_DEMO.md`
- 3D working model: `docs/simulation/kanda-rakshak-3d.html` (open it in a browser)

## Team

- **Aryan Sunil Yadav**, team lead: software, dashboards, Marathi voice
- **Sarvejeet More**, hardware lead: sensors and firmware

B.Tech CSE, MIT ADT University, Pune · arusy5558@gmail.com
