"""Generate docs/hardware/wiring.svg — block wiring diagram for the Kanda Rakshak PoC.

Pins must match firmware/include/config.h and docs/hardware/HARDWARE.md §3.
Run: python tools/make_wiring_svg.py
"""
from pathlib import Path

W, H = 1500, 980
C = {
    "v12": "#E8710A", "v5": "#D93025", "v33": "#B8860B", "gnd": "#202124",
    "sig": "#188038", "ana": "#1A73E8", "box": "#F8F9FA", "edge": "#5F6368",
    "esp": "#1B2A5C", "text": "#202124", "muted": "#5F6368",
}
out = []


def rect(x, y, w, h, fill=C["box"], stroke=C["edge"], rx=10, sw=2):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def text(x, y, s, size=15, color=C["text"], weight="normal", anchor="start"):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out.append(f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{s}</text>')


def wire(points, color, w=3, dash=None):
    d = " ".join(f"{x},{y}" for x, y in points)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round"{da}/>')


def dot(x, y, color):
    out.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')


def resistor(x, y, label, vertical=True):
    if vertical:
        rect(x - 9, y, 18, 44, fill="#FFF7E0", stroke="#8B6914", rx=3)
        text(x + 16, y + 27, label, 13, C["muted"])
    else:
        rect(x, y - 9, 44, 18, fill="#FFF7E0", stroke="#8B6914", rx=3)
        text(x + 4, y - 14, label, 13, C["muted"])


out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
out.append(f'<rect width="{W}" height="{H}" fill="white"/>')
text(40, 42, "Kanda Rakshak PoC v0.1 — wiring diagram", 26, C["esp"], "bold")
text(40, 68, "Pins = firmware/include/config.h. Measure buck output = 5.0 V BEFORE connecting the ESP32. All grounds common.", 15, C["muted"])

# ---------------- power ----------------
rect(40, 100, 190, 80)
text(55, 130, "12 V 2 A DC adapter", 16, weight="bold")
text(55, 155, "barrel jack (+ / −)", 14, C["muted"])
rect(330, 100, 210, 80)
text(345, 130, "LM2596 buck → 5.0 V", 16, weight="bold")
text(345, 155, "IN+ IN−   |   OUT+ OUT−", 14, C["muted"])

# rails
RAIL12, RAIL5, RAILG = 215, 245, 275
wire([(230, 125), (290, 125), (290, RAIL12), (1430, RAIL12)], C["v12"], 4)
wire([(290, 125), (330, 125)], C["v12"], 4)
wire([(230, 160), (270, 160), (270, RAILG), (1430, RAILG)], C["gnd"], 4)
wire([(270, 160), (330, 160)], C["gnd"], 4)
wire([(540, 125), (600, 125), (600, RAIL5), (1430, RAIL5)], C["v5"], 4)
wire([(540, 160), (580, 160), (580, RAILG)], C["gnd"], 4)
text(1437, RAIL12 + 5, "12 V", 14, C["v12"], "bold")
text(1437, RAIL5 + 5, "5 V", 14, C["v5"], "bold")
text(1437, RAILG + 5, "GND", 14, C["gnd"], "bold")

# ---------------- ESP32 ----------------
EX, EY, EW, EH = 610, 360, 250, 470
rect(EX, EY, EW, EH, fill="#E8EBF5", stroke=C["esp"], rx=14, sw=3)
text(EX + EW / 2, EY + 34, "ESP32 DevKit V1", 20, C["esp"], "bold", "middle")
text(EX + EW / 2, EY + 56, "(ESP32-WROOM-32)", 14, C["muted"], anchor="middle")
left_pins = [("3V3", 110), ("GPIO 4", 170), ("GPIO 16", 230), ("GPIO 17", 290), ("GPIO 18", 350), ("GND", 420)]
right_pins = [("VIN (5 V)", 110), ("GPIO 34 (ADC1)", 190), ("GPIO 35 (ADC1)", 270), ("GPIO 25", 350), ("GND", 420)]
for name, dy in left_pins:
    dot(EX, EY + dy, C["esp"]); text(EX + 12, EY + dy + 5, name, 14, C["esp"], "bold")
for name, dy in right_pins:
    dot(EX + EW, EY + dy, C["esp"]); text(EX + EW - 12, EY + dy + 5, name, 14, C["esp"], "bold", "end")
text(EX + EW / 2, EY + EH - 20, "GPIO 2 = onboard status LED", 13, C["muted"], anchor="middle")

# ESP power
wire([(EX + EW, EY + 110), (EX + EW + 40, EY + 110), (EX + EW + 40, RAIL5)], C["v5"])
dot(EX + EW + 40, RAIL5, C["v5"])
wire([(EX + EW, EY + 420), (EX + EW + 25, EY + 420), (EX + EW + 25, RAILG)], C["gnd"])
dot(EX + EW + 25, RAILG, C["gnd"])
wire([(EX, EY + 420), (EX - 20, EY + 420), (EX - 20, RAILG)], C["gnd"])
dot(EX - 20, RAILG, C["gnd"])

# ---------------- DHT22 x4 ----------------
dhts = [("DHT22  TOP (heap)", "GPIO 4", 170), ("DHT22  MIDDLE (heap)", "GPIO 16", 230),
        ("DHT22  BOTTOM (heap)", "GPIO 17", 290), ("DHT22  AMBIENT (outside)", "GPIO 18", 350)]
V33X, DG = 520, 545  # 3V3 bus x, local gnd bus x
wire([(EX, EY + 110), (V33X, EY + 110), (V33X, EY + 350 + 32)], C["v33"])
text(V33X - 70, EY + 100, "3V3 bus", 13, C["v33"], "bold")
for i, (label, pin, dy) in enumerate(dhts):
    y = EY + dy - 28
    rect(60, y, 300, 52, fill="#FFFFFF")
    text(75, y + 22, label, 15, weight="bold")
    text(75, y + 42, "+  OUT  −   (module has 10 kΩ pull-up)", 12, C["muted"])
    wire([(360, y + 26), (EX, EY + dy)], C["sig"])  # OUT
    wire([(360, y + 12), (V33X, y + 12)], C["v33"], 2); dot(V33X, y + 12, C["v33"])
    wire([(360, y + 40), (DG, y + 40)], C["gnd"], 2); dot(DG, y + 40, C["gnd"])
wire([(DG, EY + 140), (DG, RAILG)], C["gnd"], 2)
dot(DG, RAILG, C["gnd"])

# ---------------- MQ sensors with dividers ----------------
def mq(x, y, name, gpio_dy, sub):
    rect(x, y, 230, 70, fill="#FFFFFF")
    text(x + 15, y + 26, name, 16, weight="bold")
    text(x + 15, y + 48, sub, 12, C["muted"])
    text(x + 15, y + 64, "VCC   GND   AO   (DO unused)", 11, C["muted"])
    # power
    wire([(x + 40, y), (x + 40, RAIL5)], C["v5"], 2); dot(x + 40, RAIL5, C["v5"])
    wire([(x + 90, y), (x + 90, RAILG)], C["gnd"], 2); dot(x + 90, RAILG, C["gnd"])
    # AO -> 10k -> node -> 20k -> GND ; node -> GPIO
    ax = x + 150
    wire([(ax, y + 70), (ax, y + 95)], C["ana"])
    resistor(ax, y + 95, "10 kΩ")
    node_y = y + 160
    wire([(ax, y + 139), (ax, node_y)], C["ana"])
    dot(ax, node_y, C["ana"])
    resistor(ax, node_y + 15, "20 kΩ")
    wire([(ax, node_y), (ax, node_y + 15)], C["ana"])
    wire([(ax, node_y + 59), (ax, node_y + 75)], C["gnd"], 2)
    text(ax + 8, node_y + 92, "→ GND", 12, C["gnd"])
    if gpio_dy == 190:   # MQ-135: straight left at node level
        wire([(ax, node_y), (EX + EW + 80, node_y), (EX + EW + 80, EY + gpio_dy), (EX + EW, EY + gpio_dy)], C["ana"])
    else:                # MQ-136: separate route below, so the two analog nets never touch
        wire([(ax, node_y), (ax - 30, node_y), (ax - 30, 610), (EX + EW + 100, 610),
              (EX + EW + 100, EY + gpio_dy), (EX + EW, EY + gpio_dy)], C["ana"])
    text(ax + 10, node_y - 8, "≤ 3.3 V", 12, C["ana"], "bold")

mq(960, 320, "MQ-135  (VOC / NH₃)", 190, "gas pod, top of heap")
mq(1220, 320, "MQ-136  (H₂S / sulphur)", 270, "gas pod, top of heap")

# ---------------- MOSFET + fan ----------------
MX, MY = 1010, 680
rect(MX, MY, 250, 120, fill="#FFFFFF")
text(MX + 15, MY + 28, "Logic-level MOSFET module", 15, weight="bold")
text(MX + 15, MY + 48, "D4184 / AO3400 (NOT IRF520)", 12, C["v5"], "bold")
text(MX + 15, MY + 72, "VIN+  VIN−   OUT+  OUT−", 12, C["muted"])
text(MX + 15, MY + 92, "TRIG/PWM   GND", 12, C["muted"])
# signal from GPIO25
wire([(EX + EW, EY + 350), (960, EY + 350), (960, MY + 88), (MX, MY + 88)], C["sig"])
text(900, EY + 342, "fan signal", 12, C["sig"], "bold")
# VIN from 12 V rail and GND
wire([(MX + 40, MY), (MX + 40, 645), (1200, 645), (1200, RAIL12)], C["v12"], 2); dot(1200, RAIL12, C["v12"])
wire([(MX + 80, MY), (MX + 80, 660), (1210, 660), (1210, RAILG)], C["gnd"], 2); dot(1210, RAILG, C["gnd"])
# fan
FX, FY = 1360, 700
out.append(f'<circle cx="{FX + 60}" cy="{FY + 60}" r="58" fill="#FFFFFF" stroke="{C["edge"]}" stroke-width="2"/>')
text(FX + 60, FY + 55, "12 V fan", 15, weight="bold", anchor="middle")
text(FX + 60, FY + 75, "≤ 0.3 A", 12, C["muted"], anchor="middle")
wire([(MX + 250, MY + 40), (FX + 2, MY + 40)], C["v12"])
text(MX + 256, MY + 32, "OUT+ → fan +", 12, C["v12"], "bold")
wire([(MX + 250, MY + 100), (FX + 2, MY + 100)], C["gnd"])
text(MX + 256, MY + 118, "OUT− → fan −", 12, C["gnd"], "bold")
text(1230, FY + 150, "Flyback diode across fan: stripe (cathode) to fan +", 12, C["muted"])

# ---------------- legend ----------------
LY = 880
items = [("12 V", C["v12"]), ("5 V", C["v5"]), ("3.3 V", C["v33"]), ("GND", C["gnd"]), ("digital signal", C["sig"]), ("analog (after divider)", C["ana"])]
x = 40
for label, col in items:
    wire([(x, LY), (x + 40, LY)], col, 5)
    text(x + 50, LY + 5, label, 14)
    x += 200
text(40, 930, "Placement: TOP/MID/BOT DHT22 inside a PVC probe stick in the heap; AMBIENT outside in shade; gas pod on top, away from fan airflow; electronics box outside the heap.", 13, C["muted"])

out.append("</svg>")
dst = Path(__file__).resolve().parents[1] / "docs" / "hardware" / "wiring.svg"
dst.write_text("\n".join(out), encoding="utf-8")
print(f"wrote {dst}")
