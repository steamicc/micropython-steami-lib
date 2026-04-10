from machine import I2C, SPI, Pin
from time import sleep_ms
import ssd1327
from wsen_pads import WSEN_PADS
from hts221 import HTS221
 
# === Ecran ===
spi = SPI(1)
dc  = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs  = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
 
# === Capteurs ===
i2c = I2C(1)
pads = WSEN_PADS(i2c)   # pression + temperature
hts  = HTS221(i2c)     # humidite
 
# === Calibration ===
print("Calibration en cours...")
temps = []
hums  = []
press = []
for _ in range(10):
    temps.append(pads.temperature())
    hums.append(hts.humidity())
    press.append(pads.pressure_hpa())
    sleep_ms(200)
 
OFFSET_TEMP = 20.0  - (sum(temps) / len(temps))
OFFSET_HUM  = 50.0  - (sum(hums)  / len(hums))
OFFSET_PRES = 1013.0 - (sum(press) / len(press))
print(f"Offset T:{OFFSET_TEMP:.2f} H:{OFFSET_HUM:.2f} P:{OFFSET_PRES:.2f}")
print("Calibration OK")
 
# === Dessin ===
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
 
def comfort_label(temp, hum, pres):
    if 18 <= temp <= 26 and 40 <= hum <= 60 and 1000 <= pres <= 1025:
        return "IDEAL", 255
    elif temp > 30 or hum > 75:
        return "CHAUD", 180
    elif temp < 15 or hum < 25:
        return "FROID", 150
    elif pres < 1000:
        return "BASSE P", 150
    elif pres > 1025:
        return "HAUTE P", 200
    else:
        return "CORRECT", 200
 
def draw_screen(temp, hum, pres):
    display.fill(0)
 
    # Bordure circulaire decorative
    draw_circle(64, 64, 62, 60)
    draw_circle(64, 64, 60, 40)
 
    # === TITRE ===
    display.text("CLIMAT", 35, 20, 255)
    draw_hline(19, 29, 90, 100)
 
    # === TEMPERATURE ===
    display.text("T", 19, 35, 120)
    temp_str = f"{temp:.1f}C"
    display.text(temp_str, 29, 35, 255)
    draw_bar_h(19, 44, 90, 5, temp, 0, 50, 220)
 
    # === HUMIDITE ===
    display.text("H", 19, 52, 120)
    hum_str = f"{hum:.1f}%"
    display.text(hum_str, 29, 52, 255)
    draw_bar_h(19, 61, 90, 5, hum, 0, 100, 180)
 
    # === PRESSION ===
    display.text("P", 19, 69, 120)
    pres_str = f"{pres:.0f}hPa"
    display.text(pres_str, 29, 69, 255)
    draw_bar_h(19, 78, 90, 5, pres, 950, 1050, 160)
 
    # === SEPARATEUR ===
    draw_hline(19, 86, 90, 70)
 
    # === CONFORT ===
    label, c_color = comfort_label(temp, hum, pres)
    cx = 64 - len(label) * 4
    display.text(label, cx, 92, c_color)
 
    # === CAPTEURS ===
    draw_hline(19, 102, 90, 50)
    display.text("PADS+HTS221", 22, 106, 60)
 
    display.show()
 
# === Boucle principale ===
print("Station climatique demarree")
while True:
    try:
        temp = pads.temperature() + OFFSET_TEMP
        hum  = hts.humidity()     + OFFSET_HUM
        pres = pads.pressure_hpa()+ OFFSET_PRES
        hum  = max(0.0, min(100.0, hum))
        print(f"T:{temp:.2f}C  H:{hum:.2f}%  P:{pres:.1f}hPa")
        draw_screen(temp, hum, pres)
    except Exception as e:
        print("Erreur:", e)
        display.fill(0)
        display.text("ERREUR", 35, 55, 255)
        display.text(str(e)[:16], 0, 70, 150)
        display.show()
    sleep_ms(1000)
 