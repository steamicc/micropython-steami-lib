"""
Exemple d'utilisation de la classe MCP23009Pin
Cet exemple montre comment utiliser les GPIO du MCP23009E comme des pins normales
"""

from time import sleep

from machine import I2C, Pin
from mcp23009e import MCP23009E, MCP23009Pin
from mcp23009e.const import *

# Configuration I2C
bus = I2C(1)

# Configuration du pin de reset
reset = Pin("RST_EXPANDER", Pin.OUT)

# Créer l'instance du driver MCP23009E
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

print("=================================")
print("Test de la classe MCP23009Pin")
print("=================================\n")

# ===== Test 1 : Utilisation basique comme Pin =====
print("Test 1 : Configuration et lecture/écriture")
print("-" * 50)

# Créer des objets Pin pour les boutons du D-PAD
btn_up = MCP23009Pin(mcp, MCP23009_BTN_UP, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
btn_down = MCP23009Pin(mcp, MCP23009_BTN_DOWN, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
btn_left = MCP23009Pin(mcp, MCP23009_BTN_LEFT, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
btn_right = MCP23009Pin(mcp, MCP23009_BTN_RIGHT, MCP23009Pin.IN, MCP23009Pin.PULL_UP)

print("✓ Boutons configurés en entrée avec pull-up")

# Afficher l'état initial
print("\nÉtat initial des boutons:")
print(f"  UP:    {btn_up.value()}")
print(f"  DOWN:  {btn_down.value()}")
print(f"  LEFT:  {btn_left.value()}")
print(f"  RIGHT: {btn_right.value()}")

# ===== Test 2 : Utilisation avec une LED (GPIO 0 par exemple) =====
print("\n\nTest 2 : Contrôle d'une LED (optionnel)")
print("-" * 50)

# Créer une pin en mode sortie pour une LED
led = MCP23009Pin(mcp, 0, MCP23009Pin.OUT)
print("✓ LED configurée sur GPIO 0")

print("\nTest des méthodes on/off/toggle:")
for i in range(3):
    print(f"  Cycle {i+1}: ON")
    led.on()
    sleep(0.3)
    print(f"  Cycle {i+1}: OFF")
    led.off()
    sleep(0.3)

print("\nTest de toggle:")
for i in range(4):
    led.toggle()
    state = "ON" if led.value() else "OFF"
    print(f"  Toggle {i+1}: {state}")
    sleep(0.3)

led.off()

# ===== Test 3 : Lecture des boutons en continu =====
print("\n\nTest 3 : Lecture en continu des boutons")
print("-" * 50)
print("Appuyez sur les boutons (Ctrl+C pour arrêter)...")

buttons = {
    "UP": btn_up,
    "DOWN": btn_down,
    "LEFT": btn_left,
    "RIGHT": btn_right,
}

try:
    last_states = dict.fromkeys(buttons.keys())

    while True:
        for name, btn in buttons.items():
            # Les boutons sont actifs à LOW
            state = btn.value()

            if last_states[name] != state:
                if state == 0:  # Bouton appuyé
                    print(f"[{name}] APPUYÉ")
                else:  # Bouton relâché
                    print(f"[{name}] RELÂCHÉ")
                last_states[name] = state

        sleep(0.05)

except KeyboardInterrupt:
    print("\n\nTest terminé!")

# ===== Test 4 : Utilisation avec l'API callable =====
print("\n\nTest 4 : Utilisation avec l'API callable pin()")
print("-" * 50)

# On peut aussi appeler directement la pin comme une fonction
test_pin = MCP23009Pin(mcp, 1, MCP23009Pin.OUT)
test_pin(1)  # Équivalent à test_pin.value(1)
print(f"Pin 1 via callable: {test_pin()}")  # Équivalent à test_pin.value()
test_pin(0)
print(f"Pin 1 via callable: {test_pin()}")

# ===== Test 5 : Reconfiguration dynamique =====
print("\n\nTest 5 : Reconfiguration dynamique")
print("-" * 50)

dynamic_pin = MCP23009Pin(mcp, 2)
print(f"Pin 2 créée sans configuration: {dynamic_pin}")

dynamic_pin.init(MCP23009Pin.OUT)
print(f"Pin 2 configurée en sortie: {dynamic_pin}")
dynamic_pin.on()
print(f"Pin 2 valeur: {dynamic_pin.value()}")

dynamic_pin.init(MCP23009Pin.IN, MCP23009Pin.PULL_UP)
print(f"Pin 2 reconfigurée en entrée avec pull-up: {dynamic_pin}")
print(f"Pin 2 valeur: {dynamic_pin.value()}")

print("\n=================================")
print("Tous les tests terminés avec succès!")
print("=================================")
