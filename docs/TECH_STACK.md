# Tech Stack — decisions, reasons, rejected options

Reviewed 20 Oct 2026 for a 10-day prototype that must also make sense as the first step of a real field product. Rule: choose boring, proven, cheap, available in Pune within 48 h.

## Hardware

| Part | Choice | Why | Rejected |
|---|---|---|---|
| MCU | **ESP32-WROOM-32 DevKit V1** | WiFi built in, 18 ADC channels, ₹400–500, huge community, PlatformIO support | Arduino Uno (no WiFi, 5 V logic), Raspberry Pi (power hungry, SD corruption in the field, overkill) |
| Temp/RH in heap | **DHT22 (AM2302) ×3 + 1 ambient** | ±0.5 °C / ±2–5 % RH, one-wire, one GPIO each, cheap, available | SHT31 (better, but only 2 I²C addresses → needs a multiplexer for 4 sensors; use in v2) |
| Rot gas | **MQ-135** (VOC/NH₃) + **MQ-136** (H₂S / sulphur volatiles) | Metal-oxide sensors are the basis of published onion-rot "e-nose" research; cheap; analog | Electrochemical H₂S sensors (accurate but ₹3–8k each); SCD40 CO₂ (₹2.5k, add in v2 as respiration signal) |
| Fan switch | **Logic-level MOSFET module (D4184 / AO3400 / IRLZ44N)** + flyback diode | Silent, no contact wear, PWM-capable, fully on at 3.3 V gate | Relay (clicks, wears out, coil current), **IRF520 module (NOT logic-level, half-on at 3.3 V, gets hot)** |
| Fan | 12 V DC, 80–120 mm, ≤ 0.3 A | Standard, cheap, solar-friendly in v2 | AC fans (mains in a damp shed is a safety issue) |
| Power (PoC) | 12 V 2 A adapter → LM2596 buck → 5 V | One input, enough headroom | USB-only (cannot run fan + heaters reliably) |
| Power (field v2) | 20 W panel + 12 V 7 Ah SLA/LiFePO₄ + PWM controller | Sheds have no grid power | — |
| Comms (PoC) | WiFi to laptop / hotspot | Fastest to build | — |
| Comms (field v2) | **A7670C 4G/2G LTE Cat-1 module** | 2G is being phased out; Cat-1 falls back and supports SMS | SIM800L (2G-only, 2 A spikes, network sunset risk) |

## Firmware
| Item | Choice | Why |
|---|---|---|
| Toolchain | PlatformIO + Arduino framework (espressif32) | reproducible builds (`platformio.ini` pins versions), works in CI |
| Libraries | `adafruit/DHT sensor library`, `adafruit/Adafruit Unified Sensor`, `bblanchon/ArduinoJson@^7` | most used, maintained |
| Transport | HTTP POST JSON every 30 s (demo) / 15 min (field) | simplest, debuggable with curl; MQTT is v2 if we scale to thousands of devices |
| Autonomy | Fan rule on device + bounded offline ring buffer | works with no network (core claim) |

## Backend
| Item | Choice | Why | Rejected |
|---|---|---|---|
| Language | Python 3.11 | team knows it, fast to write | Node (fine, but one language is better) |
| API | FastAPI + Uvicorn | typed validation (pydantic), auto docs at `/docs` | Flask (manual validation) |
| DB | SQLite (stdlib `sqlite3`) | zero setup, file-based, perfect for 1–100 devices; Postgres/Timescale in v2 | Firebase (vendor lock-in, weaker offline story for queries) |
| HTTP client | httpx | async + timeouts | requests (no async) |
| Config | python-dotenv | `.env` file, gitignored | — |
| Tests | pytest + FastAPI TestClient | standard | — |

## Data sources
| Data | Source | Notes |
|---|---|---|
| Mandi price | **data.gov.in "Current Daily Price of Various Commodities from Various Markets (Mandi)"** (Agmarknet). Default resource id `9ef84268-d588-465a-a308-a864a43d0070` (verify on Day 1 with `tools/check_price_api.py`) | Free API key. Fields include state, district, market, commodity, variety, arrival_date, min/max/modal price (₹/quintal). Only *current* day; some markets missing on some days → we cache every fetch and fall back to the nearest market, always labelled |

## Notifications
| Stage | Channel | Why |
|---|---|---|
| Demo | **Telegram bot**: Marathi text + Marathi voice note | Free, instant, reliable on camera, supports audio |
| Pilot/production | SMS + IVR voice call via a DLT-registered provider (e.g. Exotel, Fast2SMS DLT route) | Indian telecom rules (TRAI DLT) require registered templates for business SMS; Fast2SMS's non-DLT "Quick SMS" route is manually approved per message, so it is too slow for a live demo |
| Marathi voice | **gTTS (`lang="mr"`)** for demo audio | Works today without registration. Production: Bhashini (Govt of India) TTS |

## Dashboard
Single `index.html` + Chart.js from CDN, served by FastAPI, polling every 5 s. No React build step: fewer moving parts in 10 days.

## Dev workflow
Git + GitHub (private), GitHub Actions CI (pytest + `pio run`), Claude Code with sub-agents in `.claude/agents/`.
