"""
Exemple simple d'utilisation des LEDs en configuration active-low

Montage requis : 3.3V → [LED] → [Résistance 220-330Ω] → GPIO

Cet exemple utilise MCP23009ActiveLowPin qui gère automatiquement
l'inversion de logique nécessaire pour ce type de montage.
"""

from time import sleep

from machine import I2C, Pin
from mcp23009e import MCP23009E, MCP23009ActiveLowPin
from mcp23009e.const import *

# Configuration I2C
bus = I2C(1)
reset = Pin("RST_EXPANDER", Pin.OUT)

# Créer l'instance du driver
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

print("=" * 50)
print("Test simple de LEDs - Configuration active-low")
print("=" * 50)
print("\nMontage: 3.3V → [LED] → [R] → GPIO\n")

# Créer des objets LED (la logique est automatiquement inversée)
led0 = MCP23009ActiveLowPin(mcp, 0)
led1 = MCP23009ActiveLowPin(mcp, 1)
led2 = MCP23009ActiveLowPin(mcp, 2)
led3 = MCP23009ActiveLowPin(mcp, 3)

leds = [led0, led1, led2, led3]

print("✓ 4 LEDs configurées sur GPIO 0-3\n")

# Test 1 : Allumer/éteindre chaque LED
print("Test 1 : Allumer/éteindre chaque LED")
print("-" * 50)
for i, led in enumerate(leds):
    print(f"LED {i}: ON")
    led.on()
    sleep(0.5)
    print(f"LED {i}: OFF")
    led.off()
    sleep(0.3)

# Test 2 : Chenillard
print("\nTest 2 : Effet chenillard (3 cycles)")
print("-" * 50)
for cycle in range(3):
    # Aller
    for led in leds:
        led.on()
        sleep(0.15)
        led.off()
    # Retour
    for led in reversed(leds):
        led.on()
        sleep(0.15)
        led.off()

# Test 3 : Clignotement synchrone
print("\nTest 3 : Clignotement synchrone (5 fois)")
print("-" * 50)
for i in range(5):
    # Allumer toutes les LEDs
    for led in leds:
        led.on()
    print("Toutes ON")
    sleep(0.3)

    # Éteindre toutes les LEDs
    for led in leds:
        led.off()
    print("Toutes OFF")
    sleep(0.3)

# Test 4 : Pattern alterné
print("\nTest 4 : Pattern alterné (5 fois)")
print("-" * 50)
for i in range(5):
    # Pattern 1 : LED 0 et 2 allumées
    led0.on()
    led1.off()
    led2.on()
    led3.off()
    print("Pattern: ON  OFF ON  OFF")
    sleep(0.3)

    # Pattern 2 : LED 1 et 3 allumées
    led0.off()
    led1.on()
    led2.off()
    led3.on()
    print("Pattern: OFF ON  OFF ON")
    sleep(0.3)

# Éteindre toutes les LEDs
for led in leds:
    led.off()

print("\n" + "=" * 50)
print("Test terminé!")
print("=" * 50)
print("\nNotez que vous utilisez led.on() et led.off()")
print("normalement, sans vous soucier de la logique inversée!")
