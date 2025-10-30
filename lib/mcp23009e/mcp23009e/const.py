from micropython import const

# Registres MCP23009E
MCP23009_IODIR = const(0x00)  # Registre de direction I/O (1=entrée, 0=sortie)
MCP23009_IPOL = const(0x01)  # Registre de polarité d'entrée
MCP23009_GPINTEN = const(0x02)  # Registre d'activation d'interruption
MCP23009_DEFVAL = const(0x03)  # Valeur par défaut pour comparaison d'interruption
MCP23009_INTCON = const(0x04)  # Registre de configuration d'interruption
MCP23009_IOCON = const(0x05)  # Registre de configuration I/O
MCP23009_GPPU = const(0x06)  # Registre de pull-up GPIO
MCP23009_INTF = const(0x07)  # Registre de flag d'interruption
MCP23009_INTCAP = const(0x08)  # Registre de capture d'interruption
MCP23009_GPIO = const(0x09)  # Registre GPIO (lecture/écriture)
MCP23009_OLAT = const(0x0A)  # Registre de latch de sortie

# Valeurs pour IOCON
MCP23009_IOCON_SEQOP = const(0x20)  # Mode d'opération séquentielle
MCP23009_IOCON_DISSLW = const(0x10)  # Désactive le slew rate
MCP23009_IOCON_ODR = const(0x04)  # Configure INT comme drain ouvert
MCP23009_IOCON_INTPOL = const(0x02)  # Polarité de la sortie INT

# Adresse I2C mise à jour pour 0x20
MCP23009_I2C_ADDR = const(0x20)

# Énumérations pour la configuration des GPIO
# Direction
MCP23009_DIR_OUTPUT = const(0)
MCP23009_DIR_INPUT = const(1)

# Pull-up
MCP23009_NO_PULLUP = const(0)
MCP23009_PULLUP = const(1)

# Polarité
MCP23009_POL_SAME = const(0)
MCP23009_POL_INVERTED = const(1)

# Niveau logique
MCP23009_LOGIC_LOW = const(0)
MCP23009_LOGIC_HIGH = const(1)

# Interruptions
MCP23009_INTEN_DISABLE = const(0)
MCP23009_INTEN_ENABLE = const(1)

# Comparaison interruption
MCP23009_INTCON_PREVIOUS_STATE = const(0)
MCP23009_INTCON_DEFVAL = const(1)

# GPIO mapping for the D-PAD
MCP23009_BTN_UP = const(7)
MCP23009_BTN_DOWN = const(5)
MCP23009_BTN_LEFT = const(6)
MCP23009_BTN_RIGHT = const(4)

# GPIO mapping for the croc connectors
MCP23009_GPIO1 = const(0)
MCP23009_GPIO2 = const(1)
MCP23009_GPIO3 = const(2)
MCP23009_GPIO4 = const(3)
MCP23009_GPIO5 = const(4)
MCP23009_GPIO6 = const(5)
MCP23009_GPIO7 = const(6)
MCP23009_GPIO8 = const(7)

MCP23009_GPIOS = (
    MCP23009_GPIO1,
    MCP23009_GPIO2,
    MCP23009_GPIO3,
    MCP23009_GPIO4,
    MCP23009_GPIO5,
    MCP23009_GPIO6,
    MCP23009_GPIO7,
    MCP23009_GPIO8,
)


class MCP23009Config:
    """
    Classe pour gérer le registre IOCON (I/O Configuration) du MCP23009E
    """

    def __init__(self, reg=0x00):
        """
        Initialise la configuration IOCON

        Args:
            reg: Valeur initiale du registre (par défaut 0x00)
        """
        self.reg = reg & 0b00100111  # Masque pour ne garder que les bits valides

    # SEQOP - Sequential Operation
    def set_seqop(self):
        """Active SEQOP : l'adresse du pointeur ne s'incrémente pas"""
        self.reg |= 0x20
        return self

    def clear_seqop(self):
        """Désactive SEQOP : l'adresse du pointeur s'incrémente"""
        self.reg &= ~0x20
        return self

    def has_seqop(self):
        """Vérifie si SEQOP est activé"""
        return (self.reg & 0x20) > 0

    # ODR - Open-Drain output
    def set_odr(self):
        """Active ODR : sortie INT en drain ouvert"""
        self.reg |= 0x04
        return self

    def clear_odr(self):
        """Désactive ODR : sortie INT en active driver"""
        self.reg &= ~0x04
        return self

    def has_odr(self):
        """Vérifie si ODR est activé"""
        return (self.reg & 0x04) > 0

    # INTPOL - INT Polarity
    def set_intpol(self):
        """Configure la polarité INT à Active-High"""
        self.reg |= 0x02
        return self

    def clear_intpol(self):
        """Configure la polarité INT à Active-Low"""
        self.reg &= ~0x02
        return self

    def has_intpol(self):
        """Vérifie si INTPOL est configuré à Active-High"""
        return (self.reg & 0x02) > 0

    # INTCC - Interrupt Clearing Control
    def set_intcc(self):
        """Active INTCC : lecture de INTCAP efface l'interruption"""
        self.reg |= 0x01
        return self

    def clear_intcc(self):
        """Désactive INTCC : lecture de GPIO efface l'interruption"""
        self.reg &= ~0x01
        return self

    def has_intcc(self):
        """Vérifie si INTCC est activé"""
        return (self.reg & 0x01) > 0

    def get_register_value(self):
        """Retourne la valeur du registre"""
        return self.reg
