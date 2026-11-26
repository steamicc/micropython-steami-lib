"""
Displays the VL53L1X distance with a scrolling line graph.

Runs on every release: steami.Distance reads the VL53L1X time-of-flight
sensor, fitted on V1a, V1b and V1c.
"""

from time import sleep_ms

from steami import Distance, Screen

# --- Display setup ---
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

# --- Sensor setup ---
distance = Distance()
distance.begin()

# --- Data buffer (scrolling window) ---
MAX_POINTS = 20
data = []

# --- Main loop ---
while True:
    mm = distance.read()
    if mm >= 0:  # -1: no target, timeout or no sensor
        data.append(mm)
        if len(data) > MAX_POINTS:
            data.pop(0)

    screen.clear()
    screen.title("Distance (mm)")
    screen.graph(data, min_val=0, max_val=1000)
    screen.subtitle("VL53L1X", "20s window")
    screen.show()

    sleep_ms(1000)
