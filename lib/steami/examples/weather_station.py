"""A weather station on four screen pages, as the Arduino WeatherStation example.

- Temperature: the temperature in the middle;
- Humidity: the humidity on a blue gauge;
- Pressure: a graph of the last 40 pressures from 950 to 1050 hPa;
- Compass: the compass rose, with its needle to the north.

RIGHT or A shows the next page, LEFT or B the previous one. On V1a/V1b a hand
swiped to the right above the gesture sensor also shows the next page.

The same file runs on V1a, V1b and V1c: the steami classes pick the sensors,
and the screen lays itself out for the panel it finds (128 px OLED with 16 grey
levels on V1a/V1b, 240 px colour TFT on V1c). V1c has no gesture sensor:
gesture.begin() prints an E20 message and returns False, and the program goes
on with the buttons alone.

A list keeps the last 40 pressures: about one reading every 200 ms, so the
curve shows about the last 8 seconds and moves to the left.

screen.begin() comes first: the V1c frame buffer is one large block of RAM, and
it is easiest to get while the heap is still empty.

If a sensor does not answer, its reading is nan: the page shows "--" in place
of the value, the curve leaves a gap, and the compass draws its rose with no
needle.
"""

import math
from time import sleep_ms

from steami import (
    Buttons,
    Compass,
    Gesture,
    Humidity,
    Pressure,
    Screen,
    Steami,
    Temperature,
)
from steami_screen import BLUE, RED

screen = Screen()
screen.begin()  # allocate the frame buffer early in the program
temperature = Temperature()
humidity = Humidity()
pressure = Pressure()
compass = Compass()
buttons = Buttons()
gesture = Gesture()  # V1a/V1b only
for function in (temperature, humidity, pressure, compass, buttons):
    function.begin()
has_gesture = gesture.begin()  # on V1c: prints E20 and returns False
Steami.print_info()

PAGES = ("Temperature", "Humidity", "Pressure", "Compass")
HISTORY = 40
history = []  # the last 40 pressures
page = 0


def one_decimal(value):
    """The value with one decimal, or "--" when it is nan."""
    return "{:.1f}".format(value) if not math.isnan(value) else "--"


def draw(page):
    screen.clear()
    if page == 0:
        screen.title(PAGES[page])
        screen.value(one_decimal(temperature.read()), unit="C")
    elif page == 1:
        h = humidity.read()
        screen.gauge(h, min_val=0, max_val=100, color=BLUE)
        screen.title(PAGES[page])
        screen.value(one_decimal(h), unit="%")
    elif page == 2:
        screen.title(PAGES[page])
        screen.graph(history, min_val=950, max_val=1050, color=RED)
        screen.subtitle("hPa")
    else:
        screen.compass(compass.heading())  # the rose fills the screen: no extra text
    screen.show()


try:
    while True:
        if buttons.was_pressed("RIGHT") or buttons.was_pressed("A"):
            page = (page + 1) % 4
        if buttons.was_pressed("LEFT") or buttons.was_pressed("B"):
            page = (page + 3) % 4
        if has_gesture and gesture.read() == Gesture.RIGHT:
            page = (page + 1) % 4
        history.append(pressure.read())
        if len(history) > HISTORY:
            history.pop(0)
        draw(page)
        sleep_ms(200)
except KeyboardInterrupt:
    pass
finally:
    screen.clear()
    screen.show()
