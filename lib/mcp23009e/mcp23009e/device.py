from machine import I2C, Pin
from time import sleep_ms


from mcp23009e.const import *

def _set_bit(reg, bit, value):
    """Modifie un bit spécifique dans un registre"""
    if value == 0:
        reg &= ~(1 << bit)
    else:
        reg |= (1 << bit)
    return reg


def _get_bit(reg, bit):
    """Lit un bit spécifique dans un registre"""
    return 1 if (reg & (1 << bit)) else 0


class MCP23009E(object):
    def __init__(self, i2c, address, reset_pin, interrupt_pin=None):
        """
        Initialise le driver MCP23009E

        Args:
            i2c: Instance I2C de MicroPython
            address: Adresse I2C du composant (par défaut 0x20)
            reset_pin: Pin de reset hardware (objet Pin)
            interrupt_pin: Pin d'interruption (optionnel, objet Pin)
        """

        self.i2c = i2c
        self.address = address
        self.reset_pin = reset_pin
        self.interrupt_pin = interrupt_pin

        # Stockage des callbacks d'interruption (8 GPIOs)
        self.events_change = [None] * 8
        self.events_fall = [None] * 8
        self.events_rise = [None] * 8

        # Configuration du pin de reset
        self.reset_pin.init(Pin.OUT)

        # Configuration du pin d'interruption si fourni
        if self.interrupt_pin is not None:
            self.interrupt_pin.init(Pin.IN)
            self.interrupt_pin.irq(trigger=Pin.IRQ_FALLING, handler=self._irq_handler)

        # Réinitialisation hardware
        self.reset()

    def reset(self):
        """Effectue un reset hardware du MCP23009E"""
        self.reset_pin.value(0)
        sleep_ms(5)
        self.reset_pin.value(1)
        sleep_ms(10)

    def _soft_reset(self):
        """Réinitialise le composant avec les valeurs par défaut"""
        # Configuration par défaut : toutes les pins en entrée
        self._write_reg(MCP23009_IODIR, 0xFF)
        # Désactiver les pull-ups
        self._write_reg(MCP23009_GPPU, 0x00)
        # Configuration IOCON par défaut
        self._write_reg(MCP23009_IOCON, 0x00)
        # Désactiver les interruptions
        self._write_reg(MCP23009_GPINTEN, 0x00)

    def setup(self, gpx, direction, pullup=MCP23009_NO_PULLUP, polarity=MCP23009_POL_SAME):
        """
        Configure un GPIO

        Args:
            gpx: Numéro de GPIO (0 à 7)
            direction: MCP_DIR_INPUT ou MCP_DIR_OUTPUT
            pullup: MCP_PULLUP ou MCP_NO_PULLUP (défaut: MCP_NO_PULLUP)
            polarity: MCP_POL_SAME ou MCP_POL_INVERTED (défaut: MCP_POL_SAME)
        """
        if gpx > 7:
            return

        # Lire les registres actuels
        iodir = self._read_reg(MCP23009_IODIR)
        gppu = self._read_reg(MCP23009_GPPU)
        ipol = self._read_reg(MCP23009_IPOL)

        # Modifier les bits appropriés
        iodir = _set_bit(iodir, gpx, direction)
        gppu = _set_bit(gppu, gpx, pullup)
        ipol = _set_bit(ipol, gpx, polarity)

        # Écrire les registres modifiés
        self._write_reg(MCP23009_IODIR, iodir)
        self._write_reg(MCP23009_GPPU, gppu)
        self._write_reg(MCP23009_IPOL, ipol)

    def set_level(self, gpx, level):
        """
        Définit le niveau logique d'un GPIO configuré en sortie

        Args:
            gpx: Numéro de GPIO (0 à 7)
            level: MCP_LOGIC_LOW ou MCP_LOGIC_HIGH
        """
        if gpx > 7:
            return

        # Vérifier que le pin est configuré en sortie
        iodir = self._read_reg(MCP23009_IODIR)
        if _get_bit(iodir, gpx) == MCP23009_DIR_INPUT:
            return  # Le pin est en entrée, on ne peut pas modifier son niveau

        # Modifier le registre GPIO
        gpio = self._read_reg(MCP23009_GPIO)
        gpio = _set_bit(gpio, gpx, level)
        self._write_reg(MCP23009_GPIO, gpio)

    def get_level(self, gpx):
        """
        Lit le niveau logique d'un GPIO

        Args:
            gpx: Numéro de GPIO (0 à 7)

        Returns:
            MCP_LOGIC_LOW ou MCP_LOGIC_HIGH
        """
        if gpx > 7:
            return MCP23009_LOGIC_LOW

        gpio = self._read_reg(MCP23009_GPIO)
        return _get_bit(gpio, gpx)

    def _write_reg(self, register, value):
        """Écrit une valeur dans un registre"""
        self.i2c.writeto_mem(self.address, register, bytes([value]))

    def _read_reg(self, register):
        """Lit une valeur depuis un registre"""
        return self.i2c.readfrom_mem(self.address, register, 1)[0]

    # ===== Accesseurs pour les registres (comme dans le driver C++) =====

    def set_iodir(self, value):
        """Définit le registre IODIR (Input/Output Direction)"""
        self._write_reg(MCP23009_IODIR, value)

    def get_iodir(self):
        """Lit le registre IODIR (Input/Output Direction)"""
        return self._read_reg(MCP23009_IODIR)

    def set_ipol(self, value):
        """Définit le registre IPOL (Input Polarity)"""
        self._write_reg(MCP23009_IPOL, value)

    def get_ipol(self):
        """Lit le registre IPOL (Input Polarity)"""
        return self._read_reg(MCP23009_IPOL)

    def set_gpinten(self, value):
        """Définit le registre GPINTEN (GPIO Interrupt Enable)"""
        self._write_reg(MCP23009_GPINTEN, value)

    def get_gpinten(self):
        """Lit le registre GPINTEN (GPIO Interrupt Enable)"""
        return self._read_reg(MCP23009_GPINTEN)

    def set_defval(self, value):
        """Définit le registre DEFVAL (Default Value)"""
        self._write_reg(MCP23009_DEFVAL, value)

    def get_defval(self):
        """Lit le registre DEFVAL (Default Value)"""
        return self._read_reg(MCP23009_DEFVAL)

    def set_intcon(self, value):
        """Définit le registre INTCON (Interrupt Control)"""
        self._write_reg(MCP23009_INTCON, value)

    def get_intcon(self):
        """Lit le registre INTCON (Interrupt Control)"""
        return self._read_reg(MCP23009_INTCON)

    def set_iocon(self, config):
        """
        Définit le registre IOCON (I/O Configuration)

        Args:
            config: Instance de MCP23009Config ou valeur entière
        """
        if isinstance(config, MCP23009Config):
            self._write_reg(MCP23009_IOCON, config.get_register_value())
        else:
            self._write_reg(MCP23009_IOCON, config)

    def get_iocon(self):
        """
        Lit le registre IOCON (I/O Configuration)

        Returns:
            Instance de MCP23009Config
        """
        return MCP23009Config(self._read_reg(MCP23009_IOCON))

    def set_gppu(self, value):
        """Définit le registre GPPU (GPIO Pull-Up)"""
        self._write_reg(MCP23009_GPPU, value)

    def get_gppu(self):
        """Lit le registre GPPU (GPIO Pull-Up)"""
        return self._read_reg(MCP23009_GPPU)

    def get_intf(self):
        """Lit le registre INTF (Interrupt Flag)"""
        return self._read_reg(MCP23009_INTF)

    def get_intcap(self):
        """Lit le registre INTCAP (Interrupt Captured value)"""
        return self._read_reg(MCP23009_INTCAP)

    def set_gpio(self, value):
        """Définit le registre GPIO"""
        self._write_reg(MCP23009_GPIO, value)

    def get_gpio(self):
        """Lit le registre GPIO"""
        return self._read_reg(MCP23009_GPIO)

    def set_olat(self, value):
        """Définit le registre OLAT (Output Latch)"""
        self._write_reg(MCP23009_OLAT, value)

    def get_olat(self):
        """Lit le registre OLAT (Output Latch)"""
        return self._read_reg(MCP23009_OLAT)

    # ===== Méthodes d'interruption =====

    def _send_enable_interrupt(self, gpx):
        """
        Active l'interruption pour un GPIO spécifique

        Args:
            gpx: Numéro de GPIO (0 à 7)
        """
        # Lire les registres actuels
        gpinten = self._read_reg(MCP23009_GPINTEN)
        intcon = self._read_reg(MCP23009_INTCON)

        # Activer l'interruption sur changement pour ce GPIO
        gpinten = _set_bit(gpinten, gpx, MCP23009_INTEN_ENABLE)
        # Configurer pour comparer avec l'état précédent
        intcon = _set_bit(intcon, gpx, MCP23009_INTCON_PREVIOUS_STATE)

        # Écrire les registres
        self._write_reg(MCP23009_GPINTEN, gpinten)
        self._write_reg(MCP23009_INTCON, intcon)

    def _send_disable_interrupt(self, gpx):
        """
        Désactive l'interruption pour un GPIO spécifique

        Args:
            gpx: Numéro de GPIO (0 à 7)
        """
        # Lire les registres actuels
        gpinten = self._read_reg(MCP23009_GPINTEN)
        intcon = self._read_reg(MCP23009_INTCON)
        defval = self._read_reg(MCP23009_DEFVAL)

        # Désactiver l'interruption pour ce GPIO
        gpinten = _set_bit(gpinten, gpx, MCP23009_INTEN_DISABLE)
        intcon = _set_bit(intcon, gpx, MCP23009_INTCON_PREVIOUS_STATE)
        defval = _set_bit(defval, gpx, MCP23009_LOGIC_LOW)

        # Écrire les registres
        self._write_reg(MCP23009_GPINTEN, gpinten)
        self._write_reg(MCP23009_INTCON, intcon)
        self._write_reg(MCP23009_DEFVAL, defval)

    def interrupt_on_change(self, gpx, callback):
        """
        Active et enregistre un callback pour les changements d'état d'un GPIO

        Args:
            gpx: Numéro de GPIO (0 à 7)
            callback: Fonction appelée lors d'un changement (reçoit le niveau logique en paramètre)
        """
        if gpx > 7:
            return

        self._send_enable_interrupt(gpx)
        self.events_change[gpx] = callback

    def interrupt_on_falling(self, gpx, callback):
        """
        Active et enregistre un callback pour les fronts descendants d'un GPIO

        Args:
            gpx: Numéro de GPIO (0 à 7)
            callback: Fonction appelée lors d'un front descendant (pas de paramètre)
        """
        if gpx > 7:
            return

        self._send_enable_interrupt(gpx)
        self.events_fall[gpx] = callback

    def interrupt_on_raising(self, gpx, callback):
        """
        Active et enregistre un callback pour les fronts montants d'un GPIO

        Args:
            gpx: Numéro de GPIO (0 à 7)
            callback: Fonction appelée lors d'un front montant (pas de paramètre)
        """
        if gpx > 7:
            return

        self._send_enable_interrupt(gpx)
        self.events_rise[gpx] = callback

    def disable_interrupt(self, gpx):
        """
        Désactive et désenregistre tous les callbacks pour un GPIO

        Args:
            gpx: Numéro de GPIO (0 à 7)
        """
        if gpx > 7:
            return

        self._send_disable_interrupt(gpx)

        # Effacer tous les callbacks pour ce GPIO
        self.events_change[gpx] = None
        self.events_fall[gpx] = None
        self.events_rise[gpx] = None

    def _irq_handler(self, pin):
        """
        Handler d'interruption appelé par MicroPython lors d'un événement IRQ
        Ce handler appelle interrupt_event pour traiter l'interruption
        """
        self.interrupt_event()

    def interrupt_event(self):
        """
        Traite les événements d'interruption du MCP23009E
        Cette méthode lit les flags d'interruption et appelle les callbacks appropriés
        """
        # Lire la configuration IOCON pour savoir comment effacer l'interruption
        iocon = self.get_iocon()

        # Lire les flags d'interruption
        intf = self._read_reg(MCP23009_INTF)

        # Lire l'état des GPIO
        if iocon.has_intcc():
            # Si INTCC est activé, lire INTCAP efface l'interruption
            state = self._read_reg(MCP23009_INTCAP)
        else:
            # Sinon, lire GPIO efface l'interruption
            state = self._read_reg(MCP23009_GPIO)

        # Traiter chaque GPIO ayant généré une interruption
        for i in range(8):
            if _get_bit(intf, i):
                level = _get_bit(state, i)

                # Appeler les callbacks appropriés
                if level == MCP23009_LOGIC_HIGH:
                    if self.events_rise[i] is not None:
                        self.events_rise[i]()
                else:
                    if self.events_fall[i] is not None:
                        self.events_fall[i]()

                # Appeler le callback de changement avec le niveau
                if self.events_change[i] is not None:
                    self.events_change[i](level)
