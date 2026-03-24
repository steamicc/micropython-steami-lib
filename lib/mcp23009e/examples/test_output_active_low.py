"""
Exemple de test des sorties pour le driver MCP23009E
CONFIGURATION ACTIVE-LOW : LED entre 3.3V et GPIO (cathode sur GPIO)

Le MCP23009E peut absorber (sink) plus de courant qu'il ne peut en fournir (source).
Pour cette raison, les LEDs doivent être connectées ainsi :
    3.3V ---[LED]---[Résistance 220-330Ω]--- GPIO

Avec ce montage :
    - GPIO LOW  → LED allumée (le MCP absorbe le courant)
    - GPIO HIGH → LED éteinte (pas de courant)

La logique est donc INVERSÉE par rapport à un montage classique.
"""

from time import sleep

from machine import I2C, Pin
from mcp23009e import MCP23009E, MCP23009Pin
from mcp23009e.const import *

# Configuration I2C
bus = I2C(1)

# Configuration du pin de reset
reset = Pin("RST_EXPANDER", Pin.OUT)

# Créer l'instance du driver
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

print("=" * 60)
print("Test des sorties MCP23009E - Configuration ACTIVE-LOW")
print("=" * 60)
print("\nMontage: 3.3V → [LED] → [Résistance] → GPIO")
print("Logique: GPIO LOW = LED ON, GPIO HIGH = LED OFF")
print("=" * 60)
print()

# ===== Classe helper pour inverser la logique =====
class ActiveLowLED:
    """
    Classe wrapper pour gérer une LED en configuration active-low
    La logique est inversée : on() met le GPIO à LOW, off() le met à HIGH
    """
    def __init__(self, mcp, gpio_num):
        self.pin = MCP23009Pin(mcp, gpio_num, MCP23009Pin.OUT)
        # Initialiser à HIGH (LED éteinte)
        self.off()

    def on(self):
        """Allume la LED (GPIO LOW)"""
        self.pin.value(0)

    def off(self):
        """Éteint la LED (GPIO HIGH)"""
        self.pin.value(1)

    def toggle(self):
        """Inverse l'état de la LED"""
        self.pin.toggle()

    def value(self, x=None):
        """
        Obtient ou définit l'état de la LED (logique inversée)
        1 = allumée, 0 = éteinte
        """
        if x is None:
            # Retourner l'état logique de la LED (inversé par rapport au GPIO)
            return 1 - self.pin.value()
        else:
            # Écrire l'état (inversé)
            self.pin.value(1 - x)

# ===== Test 1 : Test basique avec logique inversée =====
print("Test 1 : API avec logique inversée")
print("-" * 60)

# Créer des LEDs avec logique inversée
leds = []
print("Configuration des LED 0-3...")
for i in range(4):
    led = ActiveLowLED(mcp, i)
    leds.append(led)
    print(f"  LED {i} créée et initialisée (éteinte)")
print()

# Test séquentiel
print("Test séquentiel : allumer chaque LED pendant 0.5s")
for i, led in enumerate(leds):
    print(f"  LED {i}: ON")
    led.on()
    sleep(0.5)
    print(f"  LED {i}: OFF")
    led.off()
    sleep(0.3)

print()

# Test simultané
print("Test simultané : allumer toutes les LEDs")
for led in leds:
    led.on()
print("  Toutes les LEDs: ON")
sleep(1)

for led in leds:
    led.off()
print("  Toutes les LEDs: OFF")
sleep(0.5)

# ===== Test 2 : Effet chenillard =====
print("\n\nTest 2 : Effet chenillard (Knight Rider)")
print("-" * 60)
print("3 cycles d'aller-retour...")

for cycle in range(3):
    # Aller (0 -> 3)
    for i in range(4):
        leds[i].on()
        sleep(0.15)
        leds[i].off()

    # Retour (3 -> 0)
    for i in range(3, -1, -1):
        leds[i].on()
        sleep(0.15)
        leds[i].off()

print("✓ Chenillard terminé")

# ===== Test 3 : Compteur binaire =====
print("\n\nTest 3 : Compteur binaire sur 4 bits (0-15)")
print("-" * 60)

for count in range(16):
    binary = f"{count:04b}"
    print(f"  Compteur: {count:2d} = {binary}")

    for i in range(4):
        bit = int(binary[3 - i])  # LSB en premier (LED 0)
        leds[i].value(bit)

    sleep(0.4)

# Tout éteindre
for led in leds:
    led.off()

# ===== Test 4 : Test de toggle =====
print("\n\nTest 4 : Test de toggle() - 5 cycles")
print("-" * 60)

for cycle in range(5):
    print(f"  Cycle {cycle + 1}:")
    for i, led in enumerate(leds):
        led.toggle()
        state = "ON" if led.value() else "OFF"
        print(f"    LED {i}: {state}")
    sleep(0.5)

# Éteindre toutes les LEDs
for led in leds:
    led.off()

# ===== Test 5 : Patterns sur 8 LEDs =====
print("\n\nTest 5 : Patterns sur 8 LEDs (si disponibles)")
print("-" * 60)

# Créer 4 LEDs supplémentaires
print("Configuration des LED 4-7...")
for i in range(4, 8):
    led = ActiveLowLED(mcp, i)
    leds.append(led)

print()

# Patterns intéressants (ATTENTION: logique inversée pour set_gpio)
patterns = [
    (0b11111111, "Tout éteint (GPIO HIGH)"),
    (0b00000000, "Tout allumé (GPIO LOW)"),
    (0b01010101, "Pattern alterné 1"),
    (0b10101010, "Pattern alterné 2"),
    (0b00001111, "4 premiers allumés"),
    (0b11110000, "4 derniers allumés"),
]

print("Test de différents patterns:")
for pattern, description in patterns:
    print(f"  {description}: {pattern:08b}")
    # Attention: avec set_gpio, on écrit directement, donc la logique est inversée
    mcp.set_gpio(pattern)
    sleep(0.5)

# Tout éteindre (set_gpio avec 0xFF = tous HIGH = toutes LEDs éteintes)
mcp.set_gpio(0xFF)

# ===== Test 6 : PWM logiciel =====
print("\n\nTest 6 : Simulation PWM logiciel sur LED 0")
print("-" * 60)
print("Variation de luminosité...")

led0 = leds[0]

# Augmenter progressivement
print("  Augmentation de la luminosité...")
for duty in range(0, 101, 10):
    for _ in range(20):
        led0.on()
        sleep(duty / 10000)
        led0.off()
        sleep((100 - duty) / 10000)

# Diminuer progressivement
print("  Diminution de la luminosité...")
for duty in range(100, -1, -10):
    for _ in range(20):
        led0.on()
        sleep(duty / 10000)
        led0.off()
        sleep((100 - duty) / 10000)

led0.off()

# ===== Test 7 : Explication du fonctionnement =====
print("\n\n" + "=" * 60)
print("EXPLICATION TECHNIQUE")
print("=" * 60)
print()
print("Le MCP23009E peut absorber (sink) plus de courant qu'il ne peut")
print("en fournir (source). Les spécifications typiques sont:")
print("  - Sink current (IOL):   25 mA max par pin")
print("  - Source current (IOH):  ~1 mA par pin")
print()
print("C'est pourquoi le montage Active-Low est préféré:")
print()
print("  Montage Active-Low (recommandé):")
print("    3.3V → [LED] → [R] → GPIO")
print("    LED ON quand GPIO = LOW (le MCP absorbe le courant)")
print()
print("  Montage Active-High (déconseillé):")
print("    GPIO → [R] → [LED] → GND")
print("    Courant trop faible pour allumer correctement la LED")
print()
print("=" * 60)
print("Tous les tests terminés avec succès!")
print("=" * 60)
