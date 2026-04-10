from machine import I2C, SPI, Pin
from time import sleep_ms
import ssd1327
from hts221 import HTS221

# === Ecran ===
spi = SPI(1)
dc  = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs  = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# === Capteur ===
i2c = I2C(1)
sensor = HTS221(i2c)

# === Calibration ===
print("Calibration en cours...")
temps = []
hums = []
for _ in range(10):
    temps.append(sensor.temperature())
    hums.append(sensor.humidity())
    sleep_ms(200)

OFFSET_TEMP = 20.0 - (sum(temps) / len(temps))
OFFSET_HUM  = 50.0 - (sum(hums) / len(hums))
print(f"Offset T: {OFFSET_TEMP:.2f}  Offset H: {OFFSET_HUM:.2f}")
print("Calibration OK")

# === Dessin ===
# Zone safe pour ecran rond : carré 90x90 centré => x:[19,109] y:[19,109]
SAFE_X = 19
SAFE_Y = 19
SAFE_W = 90
SAFE_H = 90

def draw_hline(x, y, w, color=255):
    for i in range(w):
        display.pixel(x + i, y, color)

def draw_vline(x, y, h, color=255):
    for i in range(h):
        display.pixel(x, y + i, color)

def draw_rect(x, y, w, h, color=255):
    draw_hline(x, y, w, color)
    draw_hline(x, y + h - 1, w, color)
    draw_vline(x, y, h, color)
    draw_vline(x + w - 1, y, h, color)

def draw_fill_rect(x, y, w, h, color=255):
    for i in range(h):
        draw_hline(x, y + i, w, color)

def draw_circle(cx, cy, r, color=255):
    x = r
    y = 0
    err = 0
    while x >= y:
        display.pixel(cx + x, cy + y, color)
        display.pixel(cx + y, cy + x, color)
        display.pixel(cx - y, cy + x, color)
        display.pixel(cx - x, cy + y, color)
        display.pixel(cx - x, cy - y, color)
        display.pixel(cx - y, cy - x, color)
        display.pixel(cx + y, cy - x, color)
        display.pixel(cx + x, cy - y, color)
        y += 1
        err += 1 + 2 * y
        if 2 * (err - x) + 1 > 0:
            x -= 1
            err += 1 - 2 * x

def draw_bar_h(x, y, w, h, value, min_val, max_val, color=200):
    draw_rect(x, y, w, h, 80)
    ratio = (value - min_val) / (max_val - min_val)
    ratio = max(0.0, min(1.0, ratio))
    filled = int((w - 2) * ratio)
    if filled > 0:
        draw_fill_rect(x + 1, y + 1, filled, h - 2, color)

def comfort_label(temp, hum):
    if 18 <= temp <= 26 and 40 <= hum <= 60:
        return "OK", 255
    elif temp > 30 or hum > 75:
        return "CHAUD", 180
    elif temp < 15 or hum < 25:
        return "FROID", 150
    else:
        return "BIEN", 200

def draw_screen(temp, hum):
    display.fill(0)

    # Bordure circulaire decorative
    draw_circle(64, 64, 62, 60)
    draw_circle(64, 64, 60, 40)

    # === TITRE ===
    display.text("ENV STATION", 19, 22, 200)
    draw_hline(19, 31, 90, 80)

    # === TEMPERATURE ===
    display.text("TEMP", 19, 37, 120)
    temp_str = f"{temp:.1f}C"
    display.text(temp_str, 19, 47, 255)

    # Barre temperature (0-50C)
    draw_bar_h(19, 57, 90, 7, temp, 0, 50, 220)

    # === SEPARATEUR ===
    draw_hline(19, 67, 90, 70)

    # === HUMIDITE ===
    display.text("HUM", 19, 72, 120)
    hum_str = f"{hum:.1f}%"
    display.text(hum_str, 19, 82, 255)

    # Barre humidite (0-100%)
    draw_bar_h(19, 92, 90, 7, hum, 0, 100, 200)

    # === CONFORT ===
    label, c_color = comfort_label(temp, hum)
    draw_hline(19, 102, 90, 70)
    cx = 64 - len(label) * 4
    display.text(label, cx, 106, c_color)

    display.show()

# === Boucle principale ===
print("Station environnementale demarree")
while True:
    try:
        temp = sensor.temperature() + OFFSET_TEMP
        hum  = sensor.humidity() + OFFSET_HUM
        hum  = max(0.0, min(100.0, hum))
        print(f"T:{temp:.2f}C  H:{hum:.2f}%")
        draw_screen(temp, hum)
    except Exception as e:
        print("Erreur:", e)
        display.fill(0)
        display.text("ERREUR", 35, 55, 255)
        display.text(str(e)[:16], 0, 70, 150)
        display.show()
    sleep_ms(1000)