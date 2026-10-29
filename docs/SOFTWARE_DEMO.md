# Software demo (digital twin) — run it and film it

The hardware is still being built, so the demo runs the **real software** (backend, rule-based rot-risk score, Govt mandi-price feed, Marathi advisory, farmer app, department view) on **simulated sheds**. A simple model of the onion heap, with assumed (uncalibrated) coefficients, plays the role of the sensors. Its fan rule is modelled on the ESP32 firmware but not yet verified against it. Every simulated shed is labelled SIMULATED on screen. Simulated time is compressed: one day passes in about 2 minutes, while the chart axis shows the real clock.

## Run (Mac)
```bash
cd ~/Projects/kanda-rakshak
./scripts/demo.sh
```
Open three browser tabs:
- Shed dashboard: http://localhost:8000/?device=SIM-NSK-01
- Farmer app: http://localhost:8000/farmer?device=SIM-NSK-01
- Department view: http://localhost:8000/dept

One simulated day passes about every 2 minutes. To restart a shed from day 1, click **Restart shed** on the shed dashboard.

For a **live mandi price**, put your data.gov.in key in `backend/.env` (`DATAGOV_API_KEY=`). Without it the shed card says `NOT LIVE: manual fallback value` (only if you set `PRICE_FALLBACK_MODAL`), and the farmer app and farmer messages show **no** price. Don't film a price claim without a live key.
For **Telegram messages**, fill `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`; only `SIM-NSK-01` sends (set `NOTIFY_DEVICES`).

## The 8 demo sheds
| Shed | Village | Starts as | Why it is in the demo |
|---|---|---|---|
| SIM-NSK-01 | Lasalgaon | Monsoon humidity, kit ON | Main shed for filming |
| SIM-NSK-02 | Pimpalgaon Baswant | Rot starting | Shows rot detection + "Sort today" |
| SIM-NSK-03 | Niphad | Dry, fresh | Healthy baseline |
| SIM-NSK-04 | Yeola | Monsoon humidity, kit ON | Fan keeps it safe |
| SIM-NSK-05 | Chandwad | Dry, fresh | Healthy baseline |
| SIM-NSK-06 | Sinnar | Monsoon humidity, **kit OFF** | Traditional chawl: rots with no warning (comparison) |
| SIM-NSK-07 | Satana | Dry, fresh | Healthy baseline |
| SIM-NSK-08 | Malegaon | Rot starting | Second rot case |

## Video script (2.5 min, screen recording + voice-over)
| Time | Screen | Say |
|---|---|---|
| 0:00–0:15 | Deck slide 2 or a rotten-onion photo | "Maharashtra loses 40–60% of stored onion in traditional chawls." |
| 0:15–0:35 | 3D simulator (docs/simulation) rotating | "Kanda Rakshak fits the shed the farmer already owns: sensors at three depths, a rot-gas pod, a solar fan." |
| 0:35–0:50 | Department view | "This is our working software, running on a digital twin of 8 sheds around Nashik while the hardware is built. Sheds needing action are on top." |
| 0:50–1:20 | Shed dashboard SIM-NSK-01 → click **Rot starting** | "When rot starts, gas and heat rise inside the heap; our rot-risk score turns red and the advice changes to 'sort today'." |
| 1:20–1:40 | Click **Network OFF**, show fan still switching, then Network ON and the gap fills in | "No network? The fan decision runs on the device, and data is sent once signal returns." |
| 1:40–2:05 | Farmer app, press **ऐका (Listen)** | "The farmer gets one instruction in Marathi with the mandi price and its date, as voice. Today on Telegram; SMS and voice calls for keypad phones are planned." (Only say "today's price" if the card says *Today's mandi price*.) |
| 2:05–2:20 | Shed SIM-NSK-06 (kit OFF) vs SIM-NSK-04 (kit ON) | "In our simulation model, with assumed numbers, the same weather rots the unventilated heap. The field pilot is how we will measure the real effect." |
| 2:20–2:30 | Deck last slide | "We ask for an 80-shed pilot with the Agriculture Department." |

Record with QuickTime (File → New Screen Recording) at 1080p; add voice-over in CapCut/iMovie.

## What to say if asked "is this real?"
"The software is real and running: backend, a rule-based rot-risk score (not AI; we will only call it AI after training on pilot data), Govt price feed, Marathi advisory and dashboards. Sensor inputs are simulated by a simple heap model with assumed numbers because our hardware is being assembled, so the kit-on vs kit-off difference you see is the model's, not a measured result. The same API accepts the real ESP32, whose firmware and wiring are designed; the firmware compile and field test are still pending."
