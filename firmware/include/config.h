#pragma once
// ============================================================================
// Kanda Rakshak — hardware configuration.
// SINGLE SOURCE OF TRUTH for pins. Must match docs/hardware/HARDWARE.md §3.
// Any change here requires a hardware-safety-reviewer pass.
// ============================================================================

// ---- DHT22 (AM2302) temperature / humidity, powered from 3V3 ----
#define PIN_DHT_TOP      4    // heap top layer
#define PIN_DHT_MID      16   // heap middle layer
#define PIN_DHT_BOT      17   // heap bottom layer
#define PIN_DHT_AMB      18   // ambient, outside the heap, shaded

// ---- MQ gas sensors, powered from 5 V, analog out via 10k/20k divider ----
// ADC1 pins only (ADC2 is unusable while WiFi is on).
#define PIN_MQ135        34   // VOC / NH3
#define PIN_MQ136        35   // H2S / sulphur volatiles (optional)
#define MQ136_INSTALLED  true
#define MQ_DIVIDER_RATIO 1.5f // Vsensor = Vpin * (10k+20k)/20k

// ---- Fan via logic-level MOSFET module (D4184 / AO3400), NOT IRF520 ----
#define PIN_FAN          25
#define PIN_LED          2    // onboard LED

// ---- Timing (demo values; field values in comments) ----
#define SAMPLE_INTERVAL_MS   30000UL    // field: 900000 (15 min)
#define MQ_WARMUP_MS         180000UL   // ignore gas for 3 min after boot (first-ever use: burn in 24-48 h)
#define GAS_BASELINE_MS      600000UL   // learn clean-air/fresh baseline for 10 min after warm-up
#define HTTP_TIMEOUT_MS      5000

// ---- Fan rule (runs on device, works offline) ----
#define FAN_RH_ON            78.0f      // heap RH above this -> want ventilation
#define FAN_RH_OFF           72.0f      // hysteresis
#define FAN_TEMP_ON          30.0f      // heap temp above this -> want ventilation
#define FAN_TEMP_OFF         28.5f
#define FAN_AMB_RH_MARGIN    5.0f       // only ventilate if outside air is drier by this much
#define FAN_AMB_T_MARGIN     1.5f       // ... or cooler by this much
#define FAN_MIN_ON_MS        120000UL   // demo 2 min (field 15 min)
#define FAN_MIN_OFF_MS       120000UL
#define GAS_ALERT_RISE       0.35f      // local LED alert if gas 35 % above baseline

// ---- Offline buffer ----
#define QUEUE_LEN            96         // readings kept while offline (48 min demo / 24 h field)
