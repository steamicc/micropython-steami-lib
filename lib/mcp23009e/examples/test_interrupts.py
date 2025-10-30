"""
Exemple de test des interruptions pour le driver MCP23009E
Ce script teste les fonctionnalités d'interruption sur les boutons du D-PAD
"""

from time import sleep
from machine import I2C, Pin

from mcp23009e import MCP23009E
from mcp23009e.const import *

# Configuration I2C (à adapter selon votre carte)
bus = I2C(1)

# IMPORTANT : Le pin RST_EXPANDER n'a pas de pull-up, il DOIT être initialisé
reset = Pin("RST_EXPANDER", Pin.OUT)

# Pin d'interruption du MCP23009E
interrupt = Pin("INT_EXPANDER", Pin.IN)

# Créer l'instance avec le pin d'interruption
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset, interrupt_pin=interrupt)

print("=================================")
print("Test des interruptions MCP23009E")
print("=================================\n")

# Variables pour compter les événements
btn_counters = {
    MCP23009_BTN_UP: {"name": "UP", "press": 0, "release": 0},
    MCP23009_BTN_DOWN: {"name": "DOWN", "press": 0, "release": 0},
    MCP23009_BTN_LEFT: {"name": "LEFT", "press": 0, "release": 0},
    MCP23009_BTN_RIGHT: {"name": "RIGHT", "press": 0, "release": 0},
}

# Callbacks pour les événements
def on_button_press(btn_pin):
    """Callback appelé lors d'un appui sur un bouton"""
    def callback():
        btn_counters[btn_pin]["press"] += 1
        btn_name = btn_counters[btn_pin]["name"]
        print(f"[INTERRUPT] Bouton {btn_name} APPUYÉ")
    return callback

def on_button_release(btn_pin):
    """Callback appelé lors du relâchement d'un bouton"""
    def callback():
        btn_counters[btn_pin]["release"] += 1
        btn_name = btn_counters[btn_pin]["name"]
        print(f"[INTERRUPT] Bouton {btn_name} RELÂCHÉ")
    return callback

def on_button_change(btn_pin):
    """Callback appelé lors d'un changement d'état d'un bouton"""
    def callback(level):
        btn_name = btn_counters[btn_pin]["name"]
        state = "RELÂCHÉ" if level == MCP23009_LOGIC_HIGH else "APPUYÉ"
        print(f"[CHANGE] Bouton {btn_name} -> {state}")
    return callback

# Configuration des boutons avec interruptions
print("Configuration des interruptions sur les boutons...")
for btn_pin, info in btn_counters.items():
    # Configurer le GPIO en entrée avec pull-up
    mcp.setup(btn_pin, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)

    # Enregistrer les callbacks d'interruption
    # Les boutons sont actifs à LOW (appuyés = LOW, relâchés = HIGH)
    mcp.interrupt_on_falling(btn_pin, on_button_press(btn_pin))  # Appui
    mcp.interrupt_on_raising(btn_pin, on_button_release(btn_pin))  # Relâchement
    mcp.interrupt_on_change(btn_pin, on_button_change(btn_pin))  # Changement

print("\n✓ Configuration terminée")
print("\nAppuyez sur les boutons du D-PAD (Ctrl+C pour arrêter)...")
print("Les interruptions seront affichées automatiquement")
print("=" * 50)

try:
    while True:
        # Attendre les interruptions
        # Le handler s'exécute automatiquement
        sleep(1)

        # Afficher un résumé toutes les secondes
        # (Optionnel, commentez si vous ne voulez que les événements)
        # total = sum(c["press"] + c["release"] for c in btn_counters.values())
        # if total > 0:
        #     print(f"\n[Résumé] Total événements: {total}")

except KeyboardInterrupt:
    print("\n\n=================================")
    print("Résumé des événements:")
    print("=================================")
    for btn_pin, info in btn_counters.items():
        print(f"{info['name']:6} - Appuis: {info['press']:3}, Relâchements: {info['release']:3}")
    print("\nTest terminé!")
