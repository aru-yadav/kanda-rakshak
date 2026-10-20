// Kanda Rakshak firmware v0.1 — ESP32
// Reads 4x DHT22 + 2x MQ gas sensors, runs the fan rule locally (offline-safe),
// posts JSON to the backend, buffers readings when offline.
//
// Serial commands (115200): "fan on" | "fan off" | "fan auto" | "status"

#include <Arduino.h>
#include <initializer_list>
#include <math.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include "config.h"
#include "secrets.h"

static const char* FW_VERSION = "0.1.0";

// ---------------------------------------------------------------- sensors
DHT dhtTop(PIN_DHT_TOP, DHT22);
DHT dhtMid(PIN_DHT_MID, DHT22);
DHT dhtBot(PIN_DHT_BOT, DHT22);
DHT dhtAmb(PIN_DHT_AMB, DHT22);

struct Layer { float t; float rh; };   // NAN when invalid

struct Reading {
  uint32_t uptimeS;      // seconds since boot (backend stamps wall-clock on receipt / derives for queued)
  Layer top, mid, bot, amb;
  float mq135Mv;         // NAN while warming up
  float mq136Mv;
  bool fanOn;
  char fanMode;          // 'A' auto, 'M' manual (serial), 'R' remote override
  bool gasAlert;
};

// ---------------------------------------------------------------- state
enum FanMode { FAN_AUTO, FAN_MANUAL_ON, FAN_MANUAL_OFF };
FanMode fanMode = FAN_AUTO;
bool fanOn = false;
uint32_t fanChangedAt = 0;
int8_t remoteOverride = -1;        // -1 none, 0 off, 1 on
uint32_t remoteOverrideUntil = 0;

float gasBaseline135 = NAN, gasBaseline136 = NAN;
uint32_t baselineSamples = 0;

Reading queueBuf[QUEUE_LEN];
uint16_t qHead = 0, qCount = 0;
uint32_t droppedReadings = 0;

uint32_t lastSampleAt = 0;
Reading lastReading{};
bool haveReading = false;
uint32_t lastWifiTry = 0;
String serialLine;

// ---------------------------------------------------------------- helpers
static bool elapsed(uint32_t since, uint32_t interval) {
  return (uint32_t)(millis() - since) >= interval;      // overflow-safe
}

static bool valid(float v, float lo, float hi) { return !isnan(v) && v >= lo && v <= hi; }

static Layer readDht(DHT& d, const char* name) {
  Layer l{d.readTemperature(), d.readHumidity()};
  if (!valid(l.t, -10, 70)) { if (!isnan(l.t)) Serial.printf("[WARN] %s temp out of range: %.1f\n", name, l.t); l.t = NAN; }
  if (!valid(l.rh, 0, 100)) { l.rh = NAN; }
  if (isnan(l.t) || isnan(l.rh)) Serial.printf("[WARN] DHT %s read failed (check wiring/pin)\n", name);
  return l;
}

static float readGasMv(uint8_t pin) {
  uint32_t sum = 0;
  for (int i = 0; i < 32; i++) { sum += analogReadMilliVolts(pin); delayMicroseconds(200); }
  return (sum / 32.0f) * MQ_DIVIDER_RATIO;     // back to the sensor's own output voltage
}

static float maxOf(float a, float b, float c) {
  float m = NAN;
  for (float v : {a, b, c}) if (!isnan(v) && (isnan(m) || v > m)) m = v;
  return m;
}

static void setFan(bool on, const char* why) {
  if (on == fanOn) return;
  fanOn = on;
  fanChangedAt = millis();
  digitalWrite(PIN_FAN, on ? HIGH : LOW);
  Serial.printf("[FAN] %s (%s)\n", on ? "ON" : "OFF", why);
}

// Fan rule — runs on the device so it works with no network.
// Ventilate only when the heap is too humid/hot AND outside air is drier/cooler.
static void decideFan(const Reading& r) {
  if (fanMode == FAN_MANUAL_ON)  { setFan(true, "manual"); return; }
  if (fanMode == FAN_MANUAL_OFF) { setFan(false, "manual"); return; }
  if (remoteOverride >= 0 && (int32_t)(remoteOverrideUntil - millis()) > 0) {
    setFan(remoteOverride == 1, "remote override");
    return;
  }
  remoteOverride = -1;

  float heapRh = maxOf(r.top.rh, r.mid.rh, r.bot.rh);
  float heapT  = maxOf(r.top.t,  r.mid.t,  r.bot.t);
  if (isnan(heapRh) && isnan(heapT)) { setFan(false, "no heap data"); return; }

  bool ambOk = !isnan(r.amb.rh) && !isnan(r.amb.t);
  bool outsideDrier  = ambOk && !isnan(heapRh) && r.amb.rh < heapRh - FAN_AMB_RH_MARGIN;
  bool outsideCooler = ambOk && !isnan(heapT)  && r.amb.t  < heapT  - FAN_AMB_T_MARGIN;

  bool wantOn  = (!isnan(heapRh) && heapRh > FAN_RH_ON && outsideDrier) ||
                 (!isnan(heapT)  && heapT  > FAN_TEMP_ON && outsideCooler);
  bool wantOff = (isnan(heapRh) || heapRh < FAN_RH_OFF || !outsideDrier) &&
                 (isnan(heapT)  || heapT  < FAN_TEMP_OFF || !outsideCooler);

  if (!fanOn && wantOn && elapsed(fanChangedAt, FAN_MIN_OFF_MS)) setFan(true, "auto: heap humid/hot, outside drier/cooler");
  else if (fanOn && wantOff && elapsed(fanChangedAt, FAN_MIN_ON_MS)) setFan(false, "auto: conditions normal");
}

static void updateBaseline(float v135, float v136) {
  // Exponential moving average during the baseline window (fresh onions / clean air).
  const float a = 0.2f;
  if (!isnan(v135)) gasBaseline135 = isnan(gasBaseline135) ? v135 : (1 - a) * gasBaseline135 + a * v135;
  if (!isnan(v136)) gasBaseline136 = isnan(gasBaseline136) ? v136 : (1 - a) * gasBaseline136 + a * v136;
  baselineSamples++;
}

static Reading takeReading() {
  Reading r{};
  r.uptimeS = millis() / 1000;
  r.top = readDht(dhtTop, "top");
  r.mid = readDht(dhtMid, "mid");
  r.bot = readDht(dhtBot, "bot");
  r.amb = readDht(dhtAmb, "amb");

  bool warm = millis() > MQ_WARMUP_MS;
  r.mq135Mv = warm ? readGasMv(PIN_MQ135) : NAN;
  r.mq136Mv = (warm && MQ136_INSTALLED) ? readGasMv(PIN_MQ136) : NAN;

  if (warm && millis() < MQ_WARMUP_MS + GAS_BASELINE_MS) updateBaseline(r.mq135Mv, r.mq136Mv);

  r.gasAlert = false;
  if (!isnan(gasBaseline135) && !isnan(r.mq135Mv) && gasBaseline135 > 1 &&
      (r.mq135Mv - gasBaseline135) / gasBaseline135 > GAS_ALERT_RISE) r.gasAlert = true;
  if (!isnan(gasBaseline136) && !isnan(r.mq136Mv) && gasBaseline136 > 1 &&
      (r.mq136Mv - gasBaseline136) / gasBaseline136 > GAS_ALERT_RISE) r.gasAlert = true;

  decideFan(r);
  r.fanOn = fanOn;
  r.fanMode = fanMode != FAN_AUTO ? 'M' : (remoteOverride >= 0 ? 'R' : 'A');
  return r;
}

// ---------------------------------------------------------------- offline queue
static void enqueue(const Reading& r) {
  uint16_t idx = (qHead + qCount) % QUEUE_LEN;
  if (qCount == QUEUE_LEN) { qHead = (qHead + 1) % QUEUE_LEN; qCount--; droppedReadings++; }
  queueBuf[idx] = r;
  qCount++;
}

static void putNum(JsonObject o, const char* k, float v) { if (isnan(v)) o[k] = nullptr; else o[k] = roundf(v * 10) / 10.0f; }

static String toJson(const Reading& r) {
  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["fw"] = FW_VERSION;
  doc["uptime_s"] = r.uptimeS;
  doc["age_s"] = (millis() / 1000) - r.uptimeS;   // how old this reading is (queued ones > 0)
  JsonObject l = doc["layers"].to<JsonObject>();
  const Layer* ls[] = {&r.top, &r.mid, &r.bot, &r.amb};
  const char* names[] = {"top", "mid", "bot", "amb"};
  for (int i = 0; i < 4; i++) {
    JsonObject o = l[names[i]].to<JsonObject>();
    putNum(o, "t", ls[i]->t);
    putNum(o, "rh", ls[i]->rh);
  }
  JsonObject g = doc["gas"].to<JsonObject>();
  putNum(g, "mq135_mv", r.mq135Mv);
  putNum(g, "mq136_mv", r.mq136Mv);
  putNum(g, "mq135_base_mv", gasBaseline135);
  putNum(g, "mq136_base_mv", gasBaseline136);
  doc["gas_alert"] = r.gasAlert;
  doc["fan_on"] = r.fanOn;
  doc["fan_mode"] = String(r.fanMode);
  doc["dropped"] = droppedReadings;
  doc["rssi"] = WiFi.isConnected() ? WiFi.RSSI() : 0;
  String s; serializeJson(doc, s);
  return s;
}

// Returns true if the server accepted the reading. Parses optional fan override.
static bool postReading(const Reading& r) {
  if (!WiFi.isConnected()) return false;
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  if (!http.begin(String(API_BASE) + "/api/v1/readings")) return false;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  int code = http.POST(toJson(r));
  bool ok = code >= 200 && code < 300;
  if (ok) {
    JsonDocument resp;
    if (!deserializeJson(resp, http.getString())) {
      const char* ov = resp["fan_override"] | "auto";
      uint32_t ttl = resp["override_ttl_s"] | 0;
      if (strcmp(ov, "on") == 0 || strcmp(ov, "off") == 0) {
        remoteOverride = strcmp(ov, "on") == 0 ? 1 : 0;
        remoteOverrideUntil = millis() + ttl * 1000UL;
      } else {
        remoteOverride = -1;
      }
    }
  }
  Serial.printf("[HTTP] %d\n", code);
  http.end();
  return ok;
}

static void flushQueue() {
  while (qCount > 0 && WiFi.isConnected()) {
    if (!postReading(queueBuf[qHead])) break;
    qHead = (qHead + 1) % QUEUE_LEN;
    qCount--;
  }
}

// ---------------------------------------------------------------- wifi
static void ensureWifi() {
  if (WiFi.isConnected()) return;
  if (!elapsed(lastWifiTry, 15000) && lastWifiTry != 0) return;
  lastWifiTry = millis();
  Serial.printf("[WIFI] connecting to %s ...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);   // non-blocking; checked next loop
}

// ---------------------------------------------------------------- serial
static void printStatus(const Reading& r) {
  Serial.printf("[DATA] t=%lus TOP %.1fC %.0f%% | MID %.1fC %.0f%% | BOT %.1fC %.0f%% | AMB %.1fC %.0f%% | "
                "MQ135 %.0fmV (base %.0f) MQ136 %.0fmV (base %.0f) | fan %s | alert %s | queue %u\n",
                (unsigned long)r.uptimeS, r.top.t, r.top.rh, r.mid.t, r.mid.rh, r.bot.t, r.bot.rh,
                r.amb.t, r.amb.rh, r.mq135Mv, gasBaseline135, r.mq136Mv, gasBaseline136,
                r.fanOn ? "ON" : "OFF", r.gasAlert ? "YES" : "no", qCount);
}

static void handleSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      serialLine.trim();
      if (serialLine == "fan on")       { fanMode = FAN_MANUAL_ON;  setFan(true, "serial"); }
      else if (serialLine == "fan off") { fanMode = FAN_MANUAL_OFF; setFan(false, "serial"); }
      else if (serialLine == "fan auto"){ fanMode = FAN_AUTO; Serial.println("[FAN] auto mode"); }
      else if (serialLine == "status")  { if (haveReading) printStatus(lastReading); else Serial.println("[INFO] no reading yet"); }
      else if (serialLine.length())     { Serial.println("commands: fan on | fan off | fan auto | status"); }
      serialLine = "";
    } else if (serialLine.length() < 40) {
      serialLine += c;
    }
  }
}

// ---------------------------------------------------------------- main
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.printf("\n=== Kanda Rakshak fw %s | device %s ===\n", FW_VERSION, DEVICE_ID);
  pinMode(PIN_FAN, OUTPUT);
  digitalWrite(PIN_FAN, LOW);                  // fan OFF at boot, always
  pinMode(PIN_LED, OUTPUT);
  analogSetPinAttenuation(PIN_MQ135, ADC_11db); // 0..~3.1 V range
  analogSetPinAttenuation(PIN_MQ136, ADC_11db);
  dhtTop.begin(); dhtMid.begin(); dhtBot.begin(); dhtAmb.begin();
  Serial.printf("[INFO] MQ warm-up %lus, baseline window %lus, sample every %lus\n",
                MQ_WARMUP_MS / 1000, GAS_BASELINE_MS / 1000, SAMPLE_INTERVAL_MS / 1000);
  ensureWifi();
  lastSampleAt = millis() - SAMPLE_INTERVAL_MS + 3000;   // first sample ~3 s after boot
}

void loop() {
  handleSerial();
  ensureWifi();

  static bool wasConnected = false;
  if (WiFi.isConnected() && !wasConnected) {
    Serial.printf("[WIFI] connected, IP %s, RSSI %d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  }
  wasConnected = WiFi.isConnected();

  if (elapsed(lastSampleAt, SAMPLE_INTERVAL_MS)) {
    lastSampleAt = millis();
    Reading r = takeReading();
    lastReading = r; haveReading = true;
    printStatus(r);
    enqueue(r);
    flushQueue();
  }

  // LED: solid = gas alert, slow blink = online, fast blink = offline
  static uint32_t ledAt = 0;
  bool alert = haveReading && lastReading.gasAlert;
  uint32_t period = WiFi.isConnected() ? 1000 : 200;
  if (alert) digitalWrite(PIN_LED, HIGH);
  else if (elapsed(ledAt, period)) { ledAt = millis(); digitalWrite(PIN_LED, !digitalRead(PIN_LED)); }

  delay(10);
}
