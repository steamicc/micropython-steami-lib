"""
Exemple de test des sorties pour le driver MCP23009E
Ce script teste la configuration des GPIO en sortie et le contrôle de leur niveau
"""
import time

from machine import I2C, Pin
from mcp23009e import MCP23009E, MCP23009Pin
from mcp23009e.const import *

# Configuration I2C
bus = I2C(1)

# Configuration du pin de reset
reset = Pin("RST_EXPANDER", Pin.OUT)

# Créer l'instance du driver
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

print("=================================")
print("Test des sorties MCP23009E")
print("=================================\n")

# ===== Test 1 : Configuration de sorties avec l'API bas niveau =====
print("Test 1 : API bas niveau (MCP23009E)")
print("-" * 50)

# Configurer les GPIO 0-3 en sortie
print("Configuration des GPIO 0-3 en sortie...")
for gpio in range(4):
    mcp.setup(gpio, MCP23009_DIR_OUTPUT)
print("✓ Configuration terminée\n")

# Test séquentiel : allumer chaque GPIO un par un
print("Test séquentiel : allumer chaque GPIO pendant 0.5s")
for gpio in range(4):
    print(f"  GPIO {gpio}: HIGH")
    mcp.set_level(gpio, MCP23009_LOGIC_HIGH)
    sleep(0.5)
    print(f"  GPIO {gpio}: LOW")
    mcp.set_level(gpio, MCP23009_LOGIC_LOW)
    sleep(0.3)

print()

# Test simultané : allumer toutes les sorties ensemble
print("Test simultané : allumer toutes les sorties")
for gpio in range(4):
    mcp.set_level(gpio, MCP23009_LOGIC_HIGH)
print("  Toutes les sorties: HIGH")
sleep(1)

for gpio in range(4):
    mcp.set_level(gpio, MCP23009_LOGIC_LOW)
print("  Toutes les sorties: LOW")
sleep(0.5)

# ===== Test 2 : Configuration de sorties avec l'API Pin =====
print("\n\nTest 2 : API Pin (MCP23009Pin)")
print("-" * 50)

# Créer des objets Pin pour les GPIO 0-3
pins = []
print("Création des objets Pin...")
for i in range(4):
    pin = MCP23009Pin(mcp, i, MCP23009Pin.OUT)
    pins.append(pin)
    print(f"  Pin {i} créée: {pin}")
print()

# Test des méthodes on()/off()
print("Test des méthodes on()/off()")
for i, pin in enumerate(pins):
    print(f"  Pin {i}: ON")
    pin.on()
    sleep(0.3)
    print(f"  Pin {i}: OFF")
    pin.off()
    sleep(0.3)

print()

# Test de la méthode toggle()
print("Test de la méthode toggle() - 5 cycles")
for cycle in range(5):
    print(f"  Cycle {cycle + 1}:")
    for i, pin in enumerate(pins):
        pin.toggle()
        state = "ON" if pin.value() else "OFF"
        print(f"    Pin {i}: {state}")
    sleep(0.5)

# Éteindre toutes les pins
for pin in pins:
    pin.off()

# ===== Test 3 : Chenillard (Knight Rider effect) =====
print("\n\nTest 3 : Effet chenillard (Knight Rider)")
print("-" * 50)
print("3 cycles d'aller-retour...")

for cycle in range(3):
    # Aller (0 -> 3)
    for i in range(4):
        pins[i].on()
        sleep(0.15)
        pins[i].off()

    # Retour (3 -> 0)
    for i in range(3, -1, -1):
        pins[i].on()
        sleep(0.15)
        pins[i].off()

print("✓ Chenillard terminé")

# ===== Test 4 : Compteur binaire =====
print("\n\nTest 4 : Compteur binaire sur 4 bits (0-15)")
print("-" * 50)

for count in range(16):
    # Afficher le nombre en binaire sur les 4 GPIO
    binary = f"{count:04b}"
    print(f"  Compteur: {count:2d} = {binary}")

    for i in range(4):
        bit = int(binary[3 - i])  # LSB en premier (GPIO 0)
        pins[i].value(bit)

    sleep(0.4)

# Tout éteindre
for pin in pins:
    pin.off()

# ===== Test 5 : Contrôle direct du port (tous les GPIO en même temps) =====
print("\n\nTest 5 : Contrôle du port complet (8 bits)")
print("-" * 50)

# Configurer tous les GPIO en sortie
print("Configuration de tous les GPIO en sortie...")
for gpio in range(8):
    mcp.setup(gpio, MCP23009_DIR_OUTPUT)

# Test de patterns
patterns = [
    (0b00000000, "Tout éteint"),
    (0b11111111, "Tout allumé"),
    (0b10101010, "Pattern alterné 1"),
    (0b01010101, "Pattern alterné 2"),
    (0b11110000, "4 premiers allumés"),
    (0b00001111, "4 derniers allumés"),
]

print("\nTest de différents patterns:")
for pattern, description in patterns:
    print(f"  {description}: {pattern:08b}")
    mcp.set_gpio(pattern)
    sleep(0.5)

# Tout éteindre
mcp.set_gpio(0x00)

# ===== Test 6 : PWM logiciel (simulation) =====
print("\n\nTest 6 : Simulation PWM logiciel sur GPIO 0")
print("-" * 50)
print("Variation de luminosité (si LED connectée)...")

led = MCP23009Pin(mcp, 0, MCP23009Pin.OUT)

# Augmenter progressivement
print("  Augmentation de la luminosité...")
for duty in range(0, 101, 10):
    # Simuler le PWM avec on/off rapide
    for _ in range(20):
        led.on()
        sleep(duty / 10000)  # Temps ON
        led.off()
        sleep((100 - duty) / 10000)  # Temps OFF

# Diminuer progressivement
print("  Diminution de la luminosité...")
for duty in range(100, -1, -10):
    for _ in range(20):
        led.on()
        sleep(duty / 10000)
        led.off()
        sleep((100 - duty) / 10000)

led.off()

# ===== Test 7 : Test de performance =====
print("\n\nTest 7 : Test de performance")
print("-" * 50)


# Mesurer la vitesse de commutation
test_pin = MCP23009Pin(mcp, 0, MCP23009Pin.OUT)
cycles = 100

start = time.ticks_ms()
for _ in range(cycles):
    test_pin.on()
    test_pin.off()
end = time.ticks_ms()

elapsed = time.ticks_diff(end, start)
freq = cycles / (elapsed / 1000) if elapsed > 0 else 0

print(f"  {cycles} cycles en {elapsed} ms")
print(f"  Vitesse de commutation: ~{freq:.1f} Hz")
print(f"  Temps par commutation: ~{elapsed/cycles:.2f} ms")

print("\n=================================")
print("Tous les tests terminés avec succès!")
print("=================================")
print("\nNote: Ces tests fonctionnent sans matériel externe.")
print("Pour voir les résultats visuellement, connectez des LEDs")
print("sur les GPIO avec des résistances appropriées (220-330Ω).")
