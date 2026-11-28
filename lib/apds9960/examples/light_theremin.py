"""Light theremin example using APDS9960 and the board buzzer.

Changes the buzzer pitch based on ambient light level.
Uses a pentatonic scale for a musical, "auto-tuned" sound.
Updates hardware only when the note changes to prevent jitter.
"""

from time import sleep_ms

from apds9960 import uAPDS9960 as APDS9960
from machine import I2C
from steami import no_tone, tone

# Calibration Constants
# You may need to adjust MAX_LIGHT depending on your room's ambient lighting
MIN_LIGHT = 45
MAX_LIGHT = 570

# Musical Frequency Range (Hz) - Auto-Tuned Pentatonic Scale
PENTATONIC_NOTES = [
    131, 147, 165, 196, 220,  # Octave 3
    262, 294, 330, 392, 440,  # Octave 4
    523, 587, 659, 784, 880   # Octave 5
]
TOTAL_NOTES = len(PENTATONIC_NOTES)

# Hardware Initialization
i2c = I2C(1)
apds = APDS9960(i2c)
apds.enable_light_sensor()

print("=======================")
print("    Light Theremin     ")
print("=======================")
print("Move your hand over the sensor.")
print("Cover it completely to mute.")
print("Press Ctrl+C to exit.")

# STATE CACHE: Track the last played frequency
last_freq = 0

try:
    while True:
        light_level = apds.ambient_light()

        if light_level < MIN_LIGHT:
            # Only update hardware/console if it wasn't already muted
            if last_freq != 0:
                no_tone()
                print("Muted")
                last_freq = 0
        else:
            # Clamp the light reading to the expected range to avoid out-of-bounds errors
            clamped_light = max(MIN_LIGHT, min(light_level, MAX_LIGHT))

            # Avoid dividing by zero if MAX_LIGHT is not greater than MIN_LIGHT
            range_light = MAX_LIGHT - MIN_LIGHT
            if range_light <= 0:
                range_light = 1

            # Map the light range to an index in our note array (0 to 14)
            note_index = (clamped_light - MIN_LIGHT) * (TOTAL_NOTES - 1) // range_light

            # Fetch the perfect harmonic frequency
            freq = PENTATONIC_NOTES[note_index]

            # Update the buzzer tone
            if freq != last_freq:
                tone(freq)
                print("Light: {} | Note: {} | Freq: {} Hz".format(light_level, note_index, freq), end="\r")
                last_freq = freq

        sleep_ms(20)

except KeyboardInterrupt:
    print("\nTheremin stopped.")
finally:
    no_tone()
