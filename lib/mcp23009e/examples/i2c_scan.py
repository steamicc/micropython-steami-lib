"""
Script de scan I2C pour identifier tous les périphériques connectés
Utile pour trouver l'adresse correcte du MCP23009E
"""
from time import sleep

from machine import I2C, Pin

reset = Pin("RST_EXPANDER")
reset.init(Pin.OUT)
reset.value(0)
sleep(1)
reset.value(1)



print("=" * 60)
print("Scanner I2C - Recherche des périphériques")
print("=" * 60)
print()

# Tester les différents bus I2C disponibles
# Sur STM32, généralement I2C(1) et I2C(2) sont disponibles
for bus_num in [0, 1]:
    try:
        print(f"Scan du bus I2C({bus_num})...")
        i2c = I2C(bus_num)

        print(f"  Configuration: {i2c}")

        # Scanner toutes les adresses possibles (0x08 à 0x77)
        devices = i2c.scan()

        if devices:
            print(f"  ✓ {len(devices)} périphérique(s) trouvé(s):")
            for addr in devices:
                print(f"    - 0x{addr:02X} (décimal: {addr})")

                # Indiquer si c'est potentiellement le MCP23009E
                if addr == 0x40:
                    print("      → Pourrait être le MCP23009E (adresse par défaut)")
                elif addr in range(0x20, 0x28):
                    print("      → Pourrait être un MCP23xxx")
        else:
            print(f"  ✗ Aucun périphérique trouvé sur I2C({bus_num})")

        print()

    except Exception as e:
        print(f"  ✗ Erreur lors du scan I2C({bus_num}): {e}")
        print()

print("=" * 60)
print("Scan terminé!")
print()
print("Notes:")
print("  - L'adresse par défaut du MCP23009E est 0x40 (décimal 64)")
print("  - Les MCP23xxx standards utilisent 0x20-0x27")
print("  - Vérifiez le schéma de votre carte pour confirmer l'adresse")
print("=" * 60)
