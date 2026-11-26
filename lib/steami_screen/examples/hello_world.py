"""
hello_world.py
Basic steami_screen example:
- clear screen
- title
- value
- subtitle
- show
"""

from time import sleep_ms

from steami import Screen

# --- Display setup ---
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

# --- Demo loop ---
counter = 0

while True:
    screen.clear()
    screen.title("HELLO")
    screen.subtitle("screen", "Hello world")
    screen.value(counter, label="Demo")
    screen.show()

    counter += 1
    sleep_ms(1000)
