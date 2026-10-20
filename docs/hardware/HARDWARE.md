# Hardware Build Guide — Kanda Rakshak PoC (v0.1)

Owner: Sarvejeet. Reviewer: `hardware-safety-reviewer` agent + a second human before first power-on.
Wiring diagram: `wiring.svg` / `wiring.png` in this folder. Pin truth source: `firmware/include/config.h` (must match §3).

> **Safety first.** 12 V can't hurt you, but it can kill the ESP32 in one wrong jumper and can heat thin wires. Never connect or move wires with power on. Always measure the buck output before connecting anything to it.

---

## 1. Bill of materials (1 kit)

| # | Part | Qty | Approx ₹ | Notes |
|---|---|---|---|---|
| 1 | ESP32 DevKit V1 (ESP32-WROOM-32, 30 or 38 pin) | 1 | 450 | Check USB chip (CP2102 or CH340) and install its driver |
| 2 | DHT22 / AM2302 **module** (3-pin, pull-up on board) | 4 | 920 | 3 in heap + 1 ambient. Module type has the 10 kΩ pull-up |
| 3 | MQ-135 gas sensor module | 1 | 150 | VOC / NH₃ |
| 4 | MQ-136 gas sensor module | 1 | 600 | H₂S / sulphur. Optional if unavailable (cut list item 1) |
| 5 | Logic-level MOSFET module (D4184, AO3400, or IRLZ44N based) | 1 | 120 | **Not IRF520.** Must say "3.3 V compatible" |
| 6 | 12 V DC fan, 80–120 mm, ≤ 0.3 A | 1 | 200 | 2-wire is fine |
| 7 | Diode 1N5819 (or 1N4007) | 2 | 10 | Flyback across fan (if MOSFET module has none) |
| 8 | 12 V 2 A DC adapter + female DC barrel jack with screw terminals | 1 | 250 | |
| 9 | LM2596 buck converter module | 1 | 120 | Set to 5.0 V before use |
| 10 | Resistors: 10 kΩ ×4, 20 kΩ ×2 | — | 20 | Voltage dividers for the MQ analog outputs |
| 11 | Breadboard 830-point + jumper wires (M-M, M-F, 40 each) | 1 set | 250 | |
| 12 | 3-core wire, 3 m (for probes) + heat-shrink | 1 | 150 | |
| 13 | 20 mm PVC pipe, 1 m + end caps | 1 | 80 | Probe sticks: drill 4–5 holes near the sensor |
| 14 | Small plastic enclosure (electronics) | 1 | 150 | Keep it above and outside the onion heap |
| 15 | Ventilated plastic crates ×2 + 4 kg onions | — | 400 | Fresh crate + rot crate |
| 16 | Multimeter (if you don't own one) | 1 | 400 | Mandatory |
| | **Total** | | **≈ ₹4,200** | Field kit BOM (with solar + 4G) ≈ ₹7,600: see deck slide 4 |

---

## 2. Power budget (check before buying the adapter)

| Load | Rail | Current |
|---|---|---|
| ESP32 with WiFi transmitting (peak) | 5 V (VIN) | ~250 mA |
| MQ-135 heater (≤ 800 mW) | 5 V | ~160 mA |
| MQ-136 heater (≤ 900 mW) | 5 V | ~180 mA |
| DHT22 ×4 | 3.3 V (from ESP32) | ~6 mA |
| **5 V rail total** | | **≈ 0.6 A** (LM2596 rated 3 A → OK) |
| 12 V side for the buck (≈ 85 % efficient) | 12 V | ≈ 0.3 A |
| Fan | 12 V | ≤ 0.3 A |
| **12 V total** | | **≈ 0.6 A** (2 A adapter → 3× headroom) |

---

## 3. Pin map (single source of truth = `firmware/include/config.h`)

| Function | Part pin | → | ESP32 pin | Why this pin |
|---|---|---|---|---|
| Heap TOP temp/RH | DHT22 #1 OUT | → | **GPIO 4** | general GPIO, not strapping-critical for input |
| Heap MIDDLE temp/RH | DHT22 #2 OUT | → | **GPIO 16** | free on WROOM-32 |
| Heap BOTTOM temp/RH | DHT22 #3 OUT | → | **GPIO 17** | free on WROOM-32 |
| AMBIENT (outside) | DHT22 #4 OUT | → | **GPIO 18** | free |
| VOC gas | MQ-135 AO → divider | → | **GPIO 34** (ADC1_CH6) | ADC1 works with WiFi on; input-only pin |
| Sulphur gas | MQ-136 AO → divider | → | **GPIO 35** (ADC1_CH7) | ADC1, input-only |
| Fan switch | MOSFET module SIG/IN | → | **GPIO 25** | output, PWM-capable |
| Status LED | onboard LED | — | **GPIO 2** | built in |
| DHT22 power | VCC / GND | → | **3V3 / GND** | keeps data line at 3.3 V |
| MQ power | VCC / GND | → | **5 V rail / GND** | heaters need 5 V |
| ESP32 power | VIN / GND | ← | **5 V rail / GND** | from the buck |

**Do not use:** GPIO 0, 2 (except LED), 5, 12, 15 (boot strapping), GPIO 6–11 (flash), ADC2 pins (GPIO 0, 2, 4*, 12–15, 25–27) for analog while WiFi is on. (*GPIO 4 is fine as a digital DHT pin.)

### Voltage divider for each MQ analog output
MQ modules powered at 5 V can output up to 5 V. ESP32 GPIO max is 3.3 V.
```
MQ AO ──[10 kΩ]──┬──> ESP32 GPIO34 (or 35)
                 │
              [20 kΩ]
                 │
                GND
Vout = Vin × 20/(10+20) = 0.667 × Vin  → 5.0 V becomes 3.33 V
```
The firmware multiplies back by 1.5 (`MQ_DIVIDER_RATIO`) to report the sensor's real output voltage.

---

## 4. Build order (test each block before adding the next)

### Step A — ESP32 alone (USB power only)
1. Plug ESP32 into the laptop by USB. `cd firmware && pio run -t upload && pio device monitor`.
2. You should see the boot banner and `[WARN] DHT top: NaN` lines (no sensors yet). Onboard LED blinks.

### Step B — Power rail (ESP32 NOT connected)
1. 12 V adapter → barrel jack → buck IN+ / IN−.
2. Multimeter on buck OUT. Turn the brass screw until it reads **5.00–5.05 V**. Mark the screw with a pen.
3. Power off. Run buck OUT+ to breadboard **red rail (5 V)**, OUT− to **blue rail (GND)**.
4. Run a second wire from 12 V − (adapter ground) to the same GND rail. **All grounds common.**

### Step C — DHT22 ×4 (USB power is enough)
1. Each DHT22 module: `+` → ESP32 **3V3**, `−` → **GND**, `OUT` → its GPIO (§3).
2. Label each sensor with tape: TOP, MID, BOT, AMB.
3. Upload, open serial: all four show sensible values (e.g. 26.4 °C, 61 %). Breathe on one: its RH jumps. That proves the label → pin mapping.

### Step D — MQ sensors (needs the 5 V rail)
1. Power off. MQ VCC → **5 V rail**, GND → **GND rail**, AO → **10 kΩ** → divider node → **20 kΩ** → GND; divider node → GPIO 34 (MQ-135) / GPIO 35 (MQ-136). Leave DO unconnected.
2. Before connecting the ESP32 pin, measure the divider node with the multimeter: it must stay **below 3.3 V**.
3. ESP32 VIN → **5 V rail**, ESP32 GND → **GND rail**. Unplug USB while the external supply is on unless your board has a protection diode (most DevKit V1 boards do; still, avoid both together).
4. **Burn-in:** new MQ sensors need **24–48 h** powered on before readings stabilise. Start this on Day 4 night and leave it running. Firmware also ignores gas for the first `MQ_WARMUP_MS` after every boot.
5. Test: hold a cut onion near the sensor → gas mV rises within a minute.

### Step E — Fan via MOSFET
1. Power off. Typical D4184/AO3400 module terminals: **VIN+ / VIN−** (supply in), **OUT+ / OUT−** (load), **TRIG/PWM + GND** (signal). Wire: VIN+ → **12 V +**, VIN− → **GND**; fan red (+) → **OUT+**, fan black (−) → **OUT−**; TRIG/PWM → **GPIO 25**; signal GND → **GND rail**. (It is a low-side switch: OUT− is the MOSFET drain.) Check your module's silkscreen; if labels differ, ask before powering.
2. Flyback diode across the fan: **stripe (cathode) to fan +**, other end to fan −. Skip if the module has one built in (check the board for a diode near the output).
3. Power on. In serial monitor type `fan on` / `fan off` / `fan auto`. Fan follows.
4. Touch the MOSFET after 2 minutes ON: it should be cool. If hot, it is not logic-level → replace.

### Step F — WiFi + backend
1. Fill `firmware/include/secrets.h`: WiFi SSID/password, `API_BASE` = `http://<laptop-LAN-IP>:8000`, device id `KR-01`, token = `DEVICE_TOKEN` from `backend/.env`.
2. Laptop and ESP32 on the same WiFi / phone hotspot. Find the laptop IP: `ipconfig getifaddr en0` (Mac) / `ipconfig` (Windows) / `hostname -I` (Linux).
3. Serial shows `[HTTP] 200` every cycle; dashboard shows KR-01 live.

---

## 5. Mini-chawl assembly (Day 5)

```
                 ┌──────────── ELECTRONICS BOX (outside, above crate) ───────────┐
                 │  ESP32  buck  MOSFET  breadboard     ← 12 V adapter cable    │
                 └───┬───────┬───────┬───────────┬──────────────────────────────┘
       AMB DHT22 ●   │       │       │           │ fan cable
  (outside, shaded)  │ probe │ gas   │           │
                     │ stick │ pod   │           ▼
          ┌──────────┼───────┼───────┼─────┐  ┌──────┐
          │  GAS POD ●(MQ-135/136, top, ───┼──│ FAN  │ blows outside air
          │          │  away from fan)     │  │ 12 V │ through the slats
          │   ●TOP DHT22  ← 10 cm below top │  └──────┘
          │   ●MID DHT22  ← middle of heap  │
          │   ●BOT DHT22  ← 5 cm above floor│   ONION CRATE (ventilated)
          └─────────────────────────────────┘
```
- Probe stick: PVC pipe with the 3 DHT22s fixed inside at 3 heights, holes drilled next to each sensor, pushed vertically into the onions.
- Gas pod on top of the heap (gases rise), shielded from direct fan airflow, or it will just read fresh air.
- Ambient DHT22 outside the crate, in shade, not in the fan's exhaust.
- Electronics box is never inside the onion heap (moisture, and onion skins are flammable).
- Two crates (fresh vs rot) must be in the same room, same conditions.

---

## 6. Connecting code to hardware (what happens where)

| Event | Where | Code |
|---|---|---|
| Read 4 × DHT22 every 30 s | ESP32 | `firmware/src/main.cpp` → `readDhtAll()` |
| Read MQ mV (32-sample average, ×1.5 divider correction) | ESP32 | `readGasMv()` |
| Decide fan ON/OFF (works offline) | ESP32 | `decideFan()`: heap RH vs ambient RH, heap T vs ambient T, hysteresis + min on/off times |
| Send JSON | ESP32 → backend | `postReading()` → `POST /api/v1/readings` with `X-Device-Token` |
| Buffer if offline, flush later | ESP32 | ring buffer `queue[]`, `QUEUE_LEN` |
| Rot-risk score 0–100 | backend | `backend/app/rotrisk.py` |
| Mandi price (cached daily) | backend | `backend/app/price.py` |
| Hold / Sort / Sell text in Marathi + English | backend | `backend/app/advisory.py` |
| Telegram text + voice | backend | `backend/app/notify.py` |
| Live view | browser | `dashboard/index.html` |
| Fan override from dashboard (optional) | backend → ESP32 | returned in the POST response as `fan_override` with TTL |

---

## 7. Common faults

| Symptom | Likely cause | Fix |
|---|---|---|
| ESP32 not detected on USB | charge-only cable / missing driver | data cable; install CP210x or CH340 driver |
| Upload fails "Failed to connect" | board not in boot mode | hold **BOOT**, tap **EN**, release BOOT when "Connecting…" shows |
| DHT reads NaN | wrong pin / no pull-up / loose jumper | check §3; module type has pull-up; DHT22 needs ≥ 2 s between reads |
| Gas always 0 | pin on ADC2 or divider open | use GPIO 34/35; measure divider node |
| Gas stuck near max | divider missing (5 V into ADC) | **power off immediately**, add divider; ESP32 may be damaged |
| ESP32 resets when fan starts | brown-out from shared supply | ESP32 on buck 5 V, fan on 12 V; add 470–1000 µF capacitor across 5 V rail |
| MOSFET hot | not logic-level (IRF520) | replace with D4184/AO3400 module |
| Dashboard shows nothing | wrong `API_BASE` IP or different WiFi | check laptop IP; same network; firewall allows port 8000 |
