"""
Exemple de test basique pour le driver MCP23009E
Ce script teste les fonctionnalités de base : configuration GPIO, lecture/écriture
"""

from time import sleep

from machine import I2C, Pin
from mcp23009e import MCP23009E
from mcp23009e.const import *

# Configuration I2C (à adapter selon votre carte)
# Sur STeaMi, l'I2C1 est généralement utilisé
bus = I2C(1)

# IMPORTANT : Le pin RST_EXPANDER n'a pas de pull-up, il DOIT être initialisé
# sinon le MCP23009E reste en état reset et ne répond pas sur I2C
reset = Pin("RST_EXPANDER", Pin.OUT)

mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

print("=================================")
print("Test du driver MCP23009E")
print("=================================\n")

# Test 1 : Lecture des registres par défaut
print("Test 1 : Lecture des registres initiaux")
print(f"  IODIR  : 0x{mcp.get_iodir():02X} (devrait être 0xFF - toutes entrées)")
print(f"  GPPU   : 0x{mcp.get_gppu():02X} (devrait être 0x00 - pas de pull-up)")
print(f"  GPINTEN: 0x{mcp.get_gpinten():02X} (devrait être 0x00 - pas d'interruptions)")
print(f"  IOCON  : 0x{mcp.get_iocon().get_register_value():02X} (devrait être 0x00)")

print()

# Test 2 : Configuration d'un GPIO en entrée avec pull-up
print("Test 2 : Configuration GPIO 7 en entrée avec pull-up")
mcp.setup(7, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)
print(f"  IODIR après setup: 0x{mcp.get_iodir():02X}")
print(f"  GPPU après setup : 0x{mcp.get_gppu():02X}")
print()

# Test 3 : Test d'un GPIO en sortie
print("\nTest 3 : Configuration GPIO en sortie")
for i in MCP23009_GPIOS:
    mcp.setup(i, MCP23009_DIR_OUTPUT)
    print(f"  LED {i}: HIGH")
    mcp.set_level(i, MCP23009_LOGIC_HIGH)
    sleep(0.5)
    print(f"  LED {i}: LOW")
    mcp.set_level(i, MCP23009_LOGIC_LOW)
    sleep(0.5)
print()

# Test 4 : Lecture du niveau logique des boutons du D-PAD
print("Test 4 : Lecture des boutons du D-PAD")
print("  (Les boutons sont normalement HIGH, appuyés = LOW)")
btn_names = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

for btn_pin, btn_name in btn_names.items():
    # Configurer tous les boutons en entrée avec pull-up
    mcp.setup(btn_pin, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)

print("\nAppuyez sur les boutons du D-PAD (Ctrl+C pour arrêter)...")
print("=" * 50)

try:
    while True:
        # Lire l'état de tous les boutons
        states = []
        for btn_pin, btn_name in btn_names.items():
            level = mcp.get_level(btn_pin)
            if level == MCP23009_LOGIC_LOW:  # Bouton appuyé
                states.append(btn_name)

        if states:
            print(f"Boutons appuyés: {', '.join(states)}")

        sleep(0.1)

except KeyboardInterrupt:
    print("\n\nTest terminé!")


print("\n=================================")
print("Tests terminés avec succès!")
print("=================================")
