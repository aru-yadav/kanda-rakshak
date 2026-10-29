# Kanda Rakshak: Round 2 Jury Prep

Read this twice before the pitch. Part A is the story. Part B covers every technical question the jury can ask, with the honest answer.

---

## Part A. The story

### For a 10-year-old (and for the first 30 seconds of the pitch)

After harvest, a farmer keeps his onions in a shed called a *kanda chawl* for 3–5 months, hoping the price goes up.

The onions are alive. They breathe and give off heat and water. If the pile gets too wet or too warm inside, onions at the bottom start to rot. Nobody can see it, because it starts deep inside the pile. By the time the farmer smells it, a big part of the stock is gone. In Maharashtra, 40–60% of onion stored this way can be lost.

The farmer also doesn't know when to sell. If he sells too early he gets a low price. If he waits too long his onions rot.

**Kanda Rakshak is a small helper you put inside the shed the farmer already has.**

1. **It feels:** a stick pushed into the pile measures how hot and how wet it is at the top, middle and bottom. A gas sensor smells rot before a human can.
2. **It acts:** if the pile is wet and the air outside is drier, it switches on a fan by itself. No phone or internet is needed for this.
3. **It thinks:** it checks today's onion price at the mandi using Government data.
4. **It tells:** every day it gives the farmer one simple instruction in Marathi, as a voice call or SMS on any phone: **थांबा (Hold), निवडा (Sort) or विका (Sell).**

### One line for the jury

> "Kanda Rakshak turns the onion shed a farmer already owns into a smart store. It senses rot early, runs the fan by itself, and tells him in Marathi whether to hold, sort or sell, using the Government's own mandi price data."

### What we have built (progress statement, say it exactly like this)

| Part | Status |
|---|---|
| Backend: data intake, rot-risk engine, Hold/Sort/Sell advice in Marathi | **Built and tested** (automated tests) |
| Live mandi price from the Government Agmarknet API (data.gov.in) | **Working**, with date and source shown |
| Farmer phone app, shed dashboard, department/FPO dashboard | **Built** |
| Messages to the farmer's phone (Telegram in the demo; SMS and voice call in production) | **Working in the demo** |
| Digital twin: 8 virtual sheds around Nashik that behave like real ones | **Running**, uses the same fan logic as the device |
| ESP32 firmware (sensors, fan control, offline buffer) | **Written**, hardware being assembled |
| Hardware kit | **Designed**, parts list and wiring done |
| Field pilot | **Proposed**: 80 sheds, Niphad–Lasalgaon |

**Why a digital twin?** "Rot takes weeks to happen in a real shed. We built a physics model of an onion heap so we could test every situation (humid monsoon, rot starting, network cut) in minutes. When the hardware is installed, the same software takes real readings with zero changes. The device sends exactly the same data format."

---

## Part B. Technical questions and answers

### 1. How does the whole system work, end to end?

```
Shed: 3 temp/humidity sensors in the heap + 1 outside + 2 gas sensors
   │  every 5 minutes
   ▼
ESP32 controller ── decides fan ON/OFF itself (works with no network)
   │  sends a small JSON message over the internet (HTTPS)
   ▼
Our server (FastAPI, Python) ── stores the reading (SQLite database)
   │
   ├── Rot-risk engine → score 0–100 → SAFE / WATCH / ROT
   ├── Price service  → today's onion price from data.gov.in (Agmarknet)
   └── Advice rules   → one action: Hold / Sort / Sell, in Marathi + English
           │
           ▼
   Farmer: SMS + voice call (any phone)    Dashboard: FPO / Agriculture Dept
```

### 2. How exactly do you fetch the mandi price?

- **Source:** the Government of India Open Government Data platform (**data.gov.in**), dataset *"Current Daily Price of Various Commodities from Various Markets (Mandi)"*, published from **Agmarknet**. APMC mandis upload their daily arrivals and prices there.
- **How:** it's a free public **REST API**. We register for an API key and our server makes an HTTPS GET request:
  `api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=…&format=json&filters[state]=Maharashtra&filters[commodity]=Onion`
- **What comes back:** JSON rows with market, variety, arrival date, and min, max and modal price in ₹ per quintal.
- **What we do with it:**
  - We pick **Lasalgaon** first (Asia's biggest onion market), then Pimpalgaon. If neither reported today, we use the state median.
  - We store every row in our database, so we build our own price history.
  - **Trend** = today's price compared with the average of the last 7 days we stored.
- **When:** at most once every 3 hours. Mandis publish once a day, so more often is pointless.
- **If the API is down:** we use the last stored price, and the screen says **"cache"** with its date. We never show an old price as today's. Every price on screen carries its **source and date**.

### 3. How does the farmer get the message?

- **Demo:** a Telegram bot (free, instant). The judges can see a real message arrive on a phone during the pitch.
- **Production:**
  - **SMS** through a licensed SMS provider. In India, business SMS must be registered on TRAI's **DLT** system with approved templates. Our messages are fixed templates, so this fits.
  - **Voice call (IVR)** through a calling provider, playing the Marathi message. This works for farmers who can't read.
- **When:** only when the advice **changes** and the new state holds for 3 readings in a row (about 15 minutes). This stops the farmer getting a flood of messages when a reading flickers.
- **Why SMS and voice and not an app:** most small farmers have basic keypad phones or unreliable mobile data. SMS and voice calls work on 2G with no internet data.

### 4. Which language model do you use for Marathi translation?

**None, and that's deliberate. This is a strength, not a weakness.**

- There are only about 6 types of advice (Hold, Consider selling, Check/ventilate, Sell this week, Sort today, Device problem). We wrote each one directly in Marathi as a fixed template and checked it as native Marathi speakers. Only the numbers change, such as the price and which layer of the pile.
- **Why not AI translation:** advice about a farmer's money must be exact every time. A language model can produce a wrong or confusing sentence, and nobody would know. Fixed templates are predictable, can be approved for DLT SMS, and cost nothing.
- **Voice:**
  - Demo: Google text-to-speech (gTTS) turns the Marathi text into audio.
  - Production plan: **Bhashini**, the Government of India's language platform, which has Marathi speech, or pre-recorded clips by a Marathi speaker for the fixed sentences.
- **Scaling to other languages:** add templates for Hindi or Kannada and check them with native speakers. It's a day's work, not a model.

### 5. Where is the AI/ML?

Be honest here. Juries respect it.

- **Today (v0):** the rot-risk score is a **transparent, rule-based formula** (below). We chose this on purpose: with no field data yet, a "black box" model would be fake. An agriculture scientist can read and check our formula.
- **After the pilot:** every shed is weighed when loaded and when emptied, so we get the true loss. That gives **labelled data**: sensor history paired with the actual rot. We then train a model to:
  1. **predict rot days in advance** from the pattern of gas, humidity and heat, and
  2. **forecast price** a few weeks ahead from Agmarknet history and arrivals,

  so the Hold/Sell advice gets smarter.
- **One-line answer:** "We built the data pipeline first. ML without real labelled data is a guess, and the pilot gives us that data."

### 6. How is the rot-risk score calculated?

Three signals, each turned into 0–100:

| Signal | What it means | 0 at | 100 at | Weight |
|---|---|---|---|---|
| **Rot gas** | Rise over this shed's own "fresh" reading | no rise | +60% | 50% |
| **Humidity** | Wettest layer of the pile | 70% | 90% | 30% |
| **Heat** | Hottest layer minus outside temperature | 0 °C | +4 °C | 20% |

Score = weighted average. **Below 35 is SAFE, 35–65 is WATCH, above 65 is ROT.**

- Gas has the biggest weight because it's the earliest direct sign of rot.
- Onion stores best at about **65–70% humidity**. Above 80–85%, fungal and bacterial rot spread fast.
- A hot spot inside the pile means onions are breathing hard or rotting.

The weights and thresholds are our starting values, to be **calibrated in the pilot** with agriculture scientists (NHRDF/KVK).

### 7. How does the gas sensor detect rot?

- Rotting onion releases **sulphur compounds** (the bad smell) and other gases such as ammonia.
- **MQ-136** reacts to sulphur gases (H₂S). **MQ-135** reacts to ammonia and similar gases.
- Cheap gas sensors are not lab-accurate, so we don't trust their absolute number. When the shed is loaded with fresh onion we record a **baseline**, and then we watch for a **rise above that baseline**. A 60% rise counts as full rot signal. This works even with low-cost sensors.

### 8. Why fans? Why not run them all the time?

- The pile makes its own heat and moisture. Moving air through it carries both away. This is the single most effective thing a farmer can do, but today it's done by guesswork.
- **The fan only helps if the outside air is drier than the air in the pile.** On a humid monsoon night, running the fan *pushes wet air in* and makes things worse.

**Our rule, which runs on the device:**
- **Turn ON** when the pile humidity is above 78% *and* outside is at least 5 points drier, or when the pile is above 30 °C *and* outside is at least 1.5 °C cooler.
- **Turn OFF** when the pile is dry enough (below 72%) or outside is no longer drier.
- The fan must stay in a state for at least 30 minutes before switching, so it doesn't flicker.

Fans are small **12 V DC** fans that can run on a **solar panel and battery**, so there's no extra electricity bill.

### 9. How does it work without internet?

Three layers:
1. **Fan control runs on the ESP32 itself.** It reads the sensors and decides with no network. The onions are protected even if the internet is down for days.
2. **Readings are stored on the device** and uploaded when the network comes back, so no data is lost. Our demo shows this with the "Cut network" button.
3. **The farmer needs no internet at all.** He receives an SMS or voice call, which works on a basic phone over 2G.

The device connects over WiFi in the demo. In the field it uses a **4G/2G SIM module**. For villages with many sheds, a LoRa radio can send data to one shared gateway at the FPO.

### 10. Why sensors at three depths?

Rot usually starts at the **bottom and middle**, where air moves least and moisture collects. A single sensor at the top (what most products use) would say "all fine" while the bottom rots. Our probe has sensors at the **top, middle and bottom**, plus one **outside** to compare against.

### 11. What does the kit cost and who pays?

- About **₹7,600** per kit (ESP32, 4 sensors, 2 gas sensors, fan, solar, enclosure).
- Our pilot target is to cut loss from about 40% to 20% or less. On a 25-tonne shed, saving 5 t of onion at ₹15/kg is about ₹75,000 in one season. **This is a target, to be measured in the pilot.**
- **Who pays:**
  - Government: add the kit to the existing onion-storage (kanda chawl) subsidy schemes, so every new subsidised shed is also smart.
  - FPOs: buy kits for their members and use the dashboard to plan collective selling.
  - Farmers: a small yearly service fee for messages.

### 12. What about competitors?

- Some startups monitor storage temperature and humidity, mostly for warehouses and cold stores, using app dashboards.
- **What's different about us:**
  1. sensors at three depths inside the onion heap, plus rot gas;
  2. a **decision** (Hold/Sort/Sell) using the live Government price, not just a graph;
  3. the fan works **offline** on the device;
  4. **Marathi voice on any phone**, so there's no app and no literacy needed;
  5. a **retrofit** to sheds that already exist, including Government-subsidised ones;
  6. a dashboard for the **Agriculture Department** showing stock at risk across the district.

### 13. What is the "digital twin" exactly? Is the data fake?

- It's a **computer model of an onion shed**: how humidity rises and falls with outside weather, how rot spreads when it's too wet, how much gas rotting onion releases, and the **exact same fan rule** as our ESP32.
- It sends data to our server in exactly the format the real device will.
- Every simulated shed has an ID starting with **SIM-** and is labelled **SIMULATED** on every screen. We never present it as field data.
- **Answer:** "Yes, the shed data is simulated, and we label it everywhere. The software, the Government price feed and the messages are real. The twin lets us prove the logic before the hardware is in a real shed."

### 14. Data privacy and security?

- Each device has its own secret token. The server rejects data without it.
- We store only shed readings, village, and the farmer's phone number for alerts. There is no Aadhaar and no bank data.
- API keys and passwords stay in config files that are never uploaded to GitHub.

### 15. Can it work for other crops?

Yes. The same kit and software work for anything stored in heaps or sacks that rots from moisture and heat: **potato, garlic, ginger, grain**. Only the thresholds and the gas baseline change. Government buffer-stock warehouses (NAFED and similar) are another market.

### 16. What will you do with the ₹10 lakh?

1. Build 100 kits: 80 pilot sheds plus spares.
2. Install them in Niphad–Lasalgaon, Nashik with one onion FPO and the Agriculture Department (MSAMB).
3. Pay for one rabi storage season of SMS and voice calls.
4. Weigh every shed at loading and emptying (80 with the kit, 20 without) to **measure the actual loss reduction**.
5. Use that data to train the ML model.

---

## Things you must NOT say

- "Our AI predicts rot." It's a rule-based score today.
- "It saves 50% loss." That's a pilot target, not a result.
- "Tested in farms." It isn't yet.
- "We use AI translation." We use fixed Marathi templates.

## 30-second live demo order during the pitch

1. Open the **department view**: 8 sheds on the map, colours by risk.
2. Show **Sinnar (kit OFF) vs Lasalgaon (kit ON)**: same weather; one rots, one stays safe.
3. Click **"Rot starts"** on a shed. It turns red, and the farmer phone shows the Marathi alert. Press 🔊 Listen.
4. **Cut network**: the fan keeps running and readings are buffered. Restore it and everything uploads.
5. Show the **real Telegram message** arriving on your phone.
6. Show the **price card** with "source: data.gov.in" and today's date.
