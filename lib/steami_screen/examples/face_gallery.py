"""
Cycle through all 6 built-in face expressions.
"""

from time import sleep_ms

from steami import Screen

# --- Display setup ---
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

faces = [
    ("happy", "HAPPY"),
    ("sad", "SAD"),
    ("surprised", "SURPRISED"),
    ("sleeping", "SLEEPING"),
    ("angry", "ANGRY"),
    ("love", "LOVE"),
]

compact = True

while True:
    compact = not compact
    for expression, label in faces:
        screen.clear()
        screen.face(expression, compact=compact)
        screen.show()
        print("Showing face:", label, "Compact:", compact)
        sleep_ms(1000)
