# Claude Code Playbook — exact prompts, in order

Open a terminal in the repo and run `claude`. Paste these one at a time. Wait for each to finish and review before the next. Commit after every green step.

## Session 0 — first time (Day 1, Aryan)
```
Read CLAUDE.md, docs/PLAN.md, docs/TECH_STACK.md and docs/hardware/HARDWARE.md fully.
Then:
1. Run ./scripts/setup.sh and `cd backend && pytest -q`. Report results.
2. Install PlatformIO if missing and run `cd firmware && pio run`. Fix any compile error with the
   firmware-engineer agent (this firmware was written without a compiler; expect small fixes).
3. Use the red-team agent on firmware/src/main.cpp and backend/app/. Save the report to docs/reviews/.
Do not change pins in config.h without the hardware-safety-reviewer agent.
```

## Session 1 — Git + GitHub (Day 1)
```
Walk me through docs/PLAN.md §0.2 step by step: git init, first commit, gh repo create (private),
dev branch, invite Sarvejeet. Run each command only after I say "go". Confirm CI runs on GitHub.
```

## Session 2 — price API (Day 1–2)
```
I've put DATAGOV_API_KEY in backend/.env. Run `python tools/check_price_api.py`.
If it fails, open the data.gov.in resource page for "Current Daily Price of Various Commodities from
Various Markets (Mandi)", confirm the resource id and filter field names, fix backend/app/price.py,
add a test with the real response shape, and rerun. Then /gate G0.
```

## Session 3 — Telegram demo channel (Day 2)
```
I created a Telegram bot. Token and my chat id are in backend/.env. Start the backend, run
`python tools/simulator.py --scenario rot`, and confirm a Marathi text + Marathi voice note
reach my phone. If the voice fails, debug notify.py. Then /gate G1.
```

## Session 4 — hardware bring-up (Day 4, Sarvejeet + Aryan)
```
Use the hardware-safety-reviewer agent to review docs/hardware/HARDWARE.md against the parts we
actually bought (list: <paste what you bought, exact module names>). Flag any mismatch,
especially the MOSFET module and the MQ modules' output voltage.
Then guide me through HARDWARE.md §4 steps A–F one at a time. After each step, I paste the
serial monitor output; you tell me PASS/FAIL and what to check.
```

## Session 5 — end to end (Day 5–6)
```
The ESP32 (KR-01) is posting to the backend. Watch /api/v1/devices/KR-01/latest for 10 minutes.
Tune FAN_RH_ON/OFF in config.h so the fan triggers in our room conditions without flapping.
Then run the offline test (TEST_PROTOCOL B7) with me. Then /redteam all, fix with blue-team, /gate G3.
```

## Session 6 — evidence (Day 7–8)
```
The fresh-vs-rot run is done (see docs/evidence/runlog.md). Run tools/export_evidence.py for
KR-01 (and KR-02 if used). Write the honest result into docs/EVIDENCE.md: numbers, what worked,
what did not. Use the data-integrity-auditor agent. Then /gate G4.
```

## Session 7 — film + deck (Day 9–10)
```
Use the demo-director agent: finalise docs/DEMO_SCRIPT.md from what the prototype really does,
give me the pre-filming checklist, and list exact deck changes (slide → text/image).
Then /jury for 10 questions. Then /gate G5.
```

## Every session ends with
```
Run pytest and pio run. Show git status. Propose a conventional commit message. Do not push to main.
```
