"""
Exemple simple d'utilisation du MCP23009E pour lire les boutons du D-PAD
Version avec lecture en polling (sans interruption)
"""

from time import sleep
from machine import I2C, Pin

from mcp23009e import MCP23009E
from mcp23009e.const import *

# Configuration I2C
bus = I2C(1)

# Configuration du pin de reset
reset = Pin("RST_EXPANDER", Pin.OUT)

# Créer l'instance du driver
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

print("=================================")
print("Test des boutons MCP23009E")
print("=================================\n")

# Configuration des boutons
btn_mapping = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

print("Configuration des boutons...")
for btn_pin in btn_mapping.keys():
    mcp.setup(btn_pin, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)
print("✓ Configuration terminée\n")

print("Appuyez sur les boutons du D-PAD (Ctrl+C pour arrêter)...")
print("=" * 50)

try:
    last_states = {}
    while True:
        # Lire l'état de tous les boutons
        for btn_pin, btn_name in btn_mapping.items():
            level = mcp.get_level(btn_pin)

            # Afficher uniquement les changements d'état
            if btn_pin not in last_states or last_states[btn_pin] != level:
                if level == MCP23009_LOGIC_LOW:
                    print(f"Bouton {btn_name} APPUYÉ")
                else:
                    print(f"Bouton {btn_name} RELÂCHÉ")
                last_states[btn_pin] = level

        sleep(0.05)  # Petite pause pour éviter de saturer le bus I2C

except KeyboardInterrupt:
    print("\n\nTest terminé!")
