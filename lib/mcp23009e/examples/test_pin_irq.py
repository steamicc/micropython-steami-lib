"""
Exemple d'utilisation de MCP23009Pin avec interruptions
Montre comment utiliser la méthode irq() compatible avec machine.Pin
"""

from time import sleep

from machine import I2C, Pin
from mcp23009e import MCP23009E, MCP23009Pin
from mcp23009e.const import *

# Configuration I2C
bus = I2C(1)

# Configuration des pins
reset = Pin("RST_EXPANDER", Pin.OUT)
interrupt = Pin("INT_EXPANDER", Pin.IN)

# Créer l'instance du driver avec support des interruptions
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset, interrupt_pin=interrupt)

print("=" * 60)
print("Test des interruptions avec MCP23009Pin")
print("=" * 60)

# Compteurs d'événements
event_counts = {
    "UP": 0,
    "DOWN": 0,
    "LEFT": 0,
    "RIGHT": 0,
}

# Callback pour les interruptions
def button_callback(pin):
    """
    Fonction appelée lors d'une interruption sur un bouton
    Compatible avec l'API Pin de MicroPython
    """
    # Identifier le bouton
    btn_names = {
        MCP23009_BTN_UP: "UP",
        MCP23009_BTN_DOWN: "DOWN",
        MCP23009_BTN_LEFT: "LEFT",
        MCP23009_BTN_RIGHT: "RIGHT",
    }

    btn_name = btn_names.get(pin._pin_number, "UNKNOWN")
    state = "APPUYÉ" if pin.value() == 0 else "RELÂCHÉ"

    event_counts[btn_name] += 1
    print(f"[IRQ] {btn_name:5} {state:8} (événement #{event_counts[btn_name]})")

# Configuration des boutons avec interruptions
print("\nConfiguration des boutons avec interruptions...")
print("-" * 60)

# Créer les pins pour les boutons
btn_up = MCP23009Pin(mcp, MCP23009_BTN_UP, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
btn_down = MCP23009Pin(mcp, MCP23009_BTN_DOWN, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
btn_left = MCP23009Pin(mcp, MCP23009_BTN_LEFT, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
btn_right = MCP23009Pin(mcp, MCP23009_BTN_RIGHT, MCP23009Pin.IN, MCP23009Pin.PULL_UP)

# Configurer les interruptions (appui ET relâchement)
btn_up.irq(handler=button_callback, trigger=MCP23009Pin.IRQ_FALLING | MCP23009Pin.IRQ_RISING)
btn_down.irq(handler=button_callback, trigger=MCP23009Pin.IRQ_FALLING | MCP23009Pin.IRQ_RISING)
btn_left.irq(handler=button_callback, trigger=MCP23009Pin.IRQ_FALLING | MCP23009Pin.IRQ_RISING)
btn_right.irq(handler=button_callback, trigger=MCP23009Pin.IRQ_FALLING | MCP23009Pin.IRQ_RISING)

print("✓ Interruptions configurées sur tous les boutons")
print("  Trigger: IRQ_FALLING | IRQ_RISING (appui et relâchement)")

print("\n" + "=" * 60)
print("Appuyez sur les boutons du D-PAD (Ctrl+C pour arrêter)")
print("=" * 60)
print()

try:
    # Boucle principale - les interruptions sont gérées automatiquement
    while True:
        sleep(1)

except KeyboardInterrupt:
    print("\n")
    print("=" * 60)
    print("Résumé des événements")
    print("=" * 60)
    for btn_name, count in event_counts.items():
        print(f"  {btn_name:5}: {count:3} événements")
    print()
    print("Test terminé!")

print("\n" + "=" * 60)
print("Note: L'API irq() de MCP23009Pin est compatible avec machine.Pin")
print("Vous pouvez remplacer un Pin natif par un MCP23009Pin sans")
print("changer votre code existant!")
print("=" * 60)
