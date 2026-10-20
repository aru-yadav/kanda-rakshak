# Kanda Rakshak — Build Plan to First Demo

**Window:** Day 1 = Tue 20 Oct 2026 → Day 10 = Thu 29 Oct 2026 (internal submit 20:00 IST). Portal deadline 30 Oct.
**Owners:** **A** = Aryan (software, team lead) · **S** = Sarvejeet (hardware)
**Rule:** no gate is skipped. A NO-GO means cut scope, not move the deadline.

---

## 0. One-time setup (Day 1, both, ~2 h)

### 0.1 Tools on both laptops
| Tool | Why | Install check |
|---|---|---|
| Git ≥ 2.40 | version control | `git --version` |
| GitHub CLI (`gh`) | create repo, PRs from terminal | `gh --version` |
| Python 3.11+ | backend | `python3 --version` |
| VS Code + PlatformIO extension (or `pip install platformio`) | ESP32 build/flash | `pio --version` |
| Claude Code | pair-programming in terminal | `claude --version` |
| CP210x / CH340 USB driver | ESP32 USB-serial (depends on your board's chip) | board shows up as a serial port |
| Multimeter | non-negotiable for the 12 V / 5 V rails | — |

### 0.2 Git + GitHub (A does this, S clones)
```bash
git config --global user.name "Aryan Sunil Yadav"
git config --global user.email "arusy5558@gmail.com"
ssh-keygen -t ed25519 -C "arusy5558@gmail.com"     # press enter for defaults
gh auth login                                       # GitHub.com → SSH → upload key
cd kanda-rakshak
git init -b main
git add . && git commit -m "chore: initial scaffold (plan, agents, firmware, backend)"
gh repo create kanda-rakshak --private --source=. --push
git checkout -b dev && git push -u origin dev
gh repo edit --default-branch dev
# invite Sarvejeet
gh api -X PUT repos/:owner/kanda-rakshak/collaborators/<sarvejeet-github-username> -f permission=push
```
Branch protection on `main` (GitHub → Settings → Branches): require PR + CI green. Free private repos may not enforce it; then it is a team rule.

### 0.3 Branching and commits
- `main` = what we demo. Only merged from `dev` at gates.
- `dev` = integration. Feature branches: `feat/fw-dht`, `feat/be-price`, `fix/fw-adc`.
- Conventional commits. One PR per feature. PR must say: what, how tested, red-team status.
- Tag every gate: `git tag g2-hw-bench && git push --tags`.

### 0.4 Claude Code session start (every time)
```bash
cd kanda-rakshak && claude
> Read CLAUDE.md and docs/PLAN.md. Run /standup.
```
Use agents explicitly when needed: "use the firmware-engineer agent to …", "/redteam backend", "/gate G2".

---

## 1. Day-by-day

### Day 1 — Tue 20 Oct — **Gate G0: ready to build**
| Who | Task |
|---|---|
| S | **Start the rot box today.** Bruise 2 kg onions (press, cut 2–3 slightly), close in a crate with a damp cloth, keep warm. Keep 2 kg fresh onions separately, dry and ventilated. Photograph both with date. |
| S | Order parts (docs/hardware/HARDWARE.md §1). Prefer same-day/next-day: Robu.in (Pune), local electronics market. |
| A | Repo + GitHub + CI (§0). Register on data.gov.in, get API key, run the price check: `python tools/check_price_api.py`. |
| A | Create Telegram bot with @BotFather (demo notification channel), note token + your chat id. |
| Both | Read CLAUDE.md. Agree on the demo loop. |

**G0 exit:** repo on GitHub with CI green · parts ordered (screenshot) · rot box started (photo) · data.gov.in returns at least one Maharashtra onion record.

### Day 2–3 — Wed 21 – Thu 22 Oct — **Gate G1: software loop on simulator**
| Who | Task |
|---|---|
| A | Backend running: readings API, SQLite, rot-risk, price client with cache, advisory (mr/en), notifier (console + Telegram). `pytest -q` green. |
| A | Dashboard: layer temps/RH, gas, fan state, risk gauge, price card with date+source, today's advice, SIMULATED badge. |
| A | `tools/simulator.py --scenario rot` drives the full loop: risk climbs, advice changes, Telegram message + Marathi voice note arrives. |
| S | Parts arrive → unbox, check each against BOM. Flash blink test to ESP32. Set buck to 5.0 V with multimeter (no load connected). |

**G1 exit:** simulator → dashboard → Telegram Marathi text + voice, end to end, recorded as a 30 s screen capture. Red team on backend: PASS.

### Day 4 — Fri 23 Oct — **Gate G2: hardware on the bench**
| Who | Task |
|---|---|
| S | Wire step by step (HARDWARE.md §4), test each block alone with `pio run -t upload` and serial monitor: DHT22 ×4 → MQ-135/136 (start the 24–48 h burn-in tonight, leave powered) → MOSFET + fan. |
| S | Flip `FAN_TEST` in serial: fan on/off from command. |
| A | Pair with S on firmware: WiFi + POST to backend on the laptop's LAN IP. |

**G2 exit:** all 4 DHT22 valid on serial · both MQ readings change when you breathe on / bring a cut onion near them · fan switches via MOSFET · `hardware-safety-reviewer` PASS · device posts to backend.

### Day 5–6 — Sat 24 – Sun 25 Oct — **Gate G3: real end-to-end loop**
| Who | Task |
|---|---|
| S | Build the "mini chawl": ventilated crate, 3 probes at top/middle/bottom, gas pod at top, ambient sensor outside, fan on one side. Enclosure for electronics, cable strain relief. |
| S+A | Real device → backend → dashboard → Telegram. Tune fan rule thresholds. |
| A | Device-offline test: stop backend / switch off WiFi → fan rule still works on device; readings buffer and flush when back. |

**G3 exit:** real loop working from real onions · offline autonomy demonstrated on video · red team (all) PASS WITH FIXES or better.

### Day 6–8 — Sun 25 – Tue 27 Oct — **Gate G4: evidence**
| Who | Task |
|---|---|
| S | Run the experiment (docs/TEST_PROTOCOL.md): fresh crate vs rot crate, same sensor kit moved or two kits, ≥ 24 h each, ideally 48 h. Don't touch thresholds mid-run. |
| A | Export graphs from the DB (`tools/export_evidence.py`), write results honestly in docs/EVIDENCE.md, including what did NOT work. |
| A | Polish dashboard, fix all red-team HIGH items. |

**G4 exit:** real fresh-vs-rot graph from our log · offline clip · `data-integrity-auditor` all OK · decision recorded: is gas separation clear? If not, the demo leads with heat/humidity + automatic fan, gas = "calibrated in pilot".

### Day 9 — Wed 28 Oct — **Filming**
Follow docs/DEMO_SCRIPT.md. Charge everything, cache price, pre-send test message, film in daylight. Edit the same night (CapCut / DaVinci Resolve). Upload unlisted to YouTube, also to Google Drive.

### Day 10 — Thu 29 Oct — **Gate G5: submit**
| Who | Task |
|---|---|
| A | Update deck: slide 3 prototype photo, slide 4 stage → Working Prototype + real graph, video link on slide 1 or 4. Match name/phone with the form. Export PDF < 10 MB. |
| Both | `/jury` mock panel, 10 questions. |
| A | **Submit by 20:00 IST.** Screenshot confirmation. Tag `v0.1-demo`, merge `dev → main`. |

**G5 exit:** CLAUDE.md §6 checklist all ticked.

---

## 2. Cut list (in order, if behind schedule)
1. Drop MQ-136, keep MQ-135 only.
2. Drop voice note, keep Marathi text.
3. Drop backend fan override, keep device-only fan rule.
4. Drop second sensor kit, move one kit between crates.
**Never cut:** real data, offline fan proof, real price with date, honest labels.

## 3. After submission (if shortlisted)
- Week 1–2: 4G modem (A7670), solar + battery, IP65 enclosure, LittleFS persistent buffer.
- Week 3–4: 2 real chawls at a Lasalgaon/Niphad FPO, weigh-in baseline.
- IVR/SMS through a DLT-registered provider; Bhashini for Marathi TTS.
- Calibrate gas thresholds with NHRDF/KVK on local varieties.
