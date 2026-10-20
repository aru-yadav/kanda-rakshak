# Test Protocol — fresh vs rotting onion (Gate G4)

Goal: produce honest evidence that the kit tells a rotting heap from a fresh one, and that the fan works offline.
Owner: Sarvejeet (run) · Aryan (export + write-up). Do not change thresholds during a run.

## A. Bench tests (Day 4, after each wiring step)
| # | Test | Pass condition | Record |
|---|---|---|---|
| B1 | DHT label check | breathing on each probe raises only that probe's RH | photo + serial log |
| B2 | Buck output | 5.00–5.05 V, no load | multimeter photo |
| B3 | Divider node | < 3.3 V with sensor powered | multimeter photo |
| B4 | MQ response | cut onion near pod → MQ mV rises within 60 s | serial log |
| B5 | Fan manual | `fan on` / `fan off` from serial | video |
| B6 | Fan auto | wet cloth near TOP probe (RH > 78 %) with drier ambient → fan ON after rule | video |
| B7 | Offline autonomy | stop backend + WiFi off → B6 still works; serial shows queue growing; restart → queue flushes | video + log |
| B8 | Brown-out | fan + both heaters on together for 10 min, no ESP32 resets | serial log |

## B. Fresh vs rot experiment (Day 6–8)
- Two crates, same room, same height, out of direct sun. Crate F = 2 kg fresh dry onions. Crate R = 2 kg onions bruised on Day 1 and kept humid.
- Either two kits (KR-01 in F, KR-02 in R) or one kit: 12 h in F, then 12 h in R, repeat once (A-B-A-B). Log which crate in `docs/evidence/runlog.md` with times.
- Leave MQ sensors powered ≥ 24 h before starting (burn-in).
- Sampling every 30 s. Do not open crates except at logged times.
- After the run: `python tools/export_evidence.py --device KR-01 --hours 48`.

## C. What we report (whatever the result)
| Metric | How |
|---|---|
| Mean MQ-135 / MQ-136 mV, fresh vs rot | from CSV |
| Max heap RH and hotspot ΔT, fresh vs rot | from CSV |
| Risk level reached in each crate | from DB |
| Fan ON minutes per crate | from CSV |
| Did the advice change correctly? | dashboard screenshots |

If the gas difference is small or noisy, we say so in EVIDENCE.md and the video leads with humidity/heat + automatic fan. Honest beats impressive.
