"""
Module fournissant une classe Pin active-low pour les configurations où
les LEDs sont connectées entre VCC et le GPIO (cathode sur le GPIO).

Dans ce type de montage :
- GPIO LOW  → LED allumée (le MCP absorbe le courant)
- GPIO HIGH → LED éteinte (pas de courant)

Le MCP23009E peut absorber (sink) jusqu'à 25mA par pin mais ne peut
fournir (source) que très peu de courant (~1mA). C'est pourquoi cette
configuration est recommandée pour les LEDs.
"""

from mcp23009e.pin import MCP23009Pin


class MCP23009ActiveLowPin:
    """
    Classe wrapper pour gérer un GPIO en configuration active-low

    Cette classe inverse la logique d'une MCP23009Pin pour s'adapter
    aux montages où le composant (LED, relais, etc.) est connecté entre
    VCC et le GPIO.

    Montage typique pour LED :
        3.3V → [LED] → [Résistance 220-330Ω] → GPIO

    Avec ce montage :
        - pin.on()  → GPIO LOW  → LED allumée
        - pin.off() → GPIO HIGH → LED éteinte

    Exemple:
        >>> from mcp23009e import MCP23009E
        >>> from mcp23009e.active_low_pin import MCP23009ActiveLowPin
        >>> mcp = MCP23009E(i2c, address=0x20, reset_pin=reset)
        >>> led = MCP23009ActiveLowPin(mcp, 0)
        >>> led.on()   # Allume la LED (GPIO = LOW)
        >>> led.off()  # Éteint la LED (GPIO = HIGH)
    """

    # Constantes (identiques à MCP23009Pin pour compatibilité)
    IN = MCP23009Pin.IN
    OUT = MCP23009Pin.OUT
    PULL_UP = MCP23009Pin.PULL_UP
    IRQ_FALLING = MCP23009Pin.IRQ_FALLING
    IRQ_RISING = MCP23009Pin.IRQ_RISING

    def __init__(self, mcp, pin_number, mode=None, pull=-1, value=None):
        """
        Initialise une pin active-low

        Args:
            mcp: Instance de MCP23009E
            pin_number: Numéro du GPIO (0 à 7)
            mode: Mode de la pin (IN ou OUT), par défaut OUT pour une LED
            pull: Configuration du pull-up (PULL_UP ou -1)
            value: Valeur initiale logique (1=on, 0=off), appliquée inversée
        """
        # Par défaut, une pin active-low est souvent utilisée en sortie (LED)
        if mode is None:
            mode = self.OUT

        # Créer la pin sous-jacente
        self._pin = MCP23009Pin(mcp, pin_number, mode, pull)

        # Si une valeur initiale est fournie, l'appliquer (inversée)
        if value is not None:
            self.value(value)
        elif mode == self.OUT:
            # Par défaut, éteindre (GPIO HIGH)
            self._pin.value(1)

    def init(self, mode=-1, pull=-1, value=None):
        """
        (Re)configure la pin

        Args:
            mode: Mode de la pin (IN ou OUT)
            pull: Configuration du pull-up
            value: Valeur initiale logique (inversée avant application)
        """
        # Reconfigurer la pin sous-jacente
        self._pin.init(mode, pull)

        # Appliquer la valeur initiale si fournie
        if value is not None:
            self.value(value)

    def value(self, x=None):
        """
        Obtient ou définit la valeur logique de la pin (avec inversion)

        Args:
            x: Nouvelle valeur logique (1=on, 0=off), ou None pour lire

        Returns:
            Si x est None, retourne la valeur logique actuelle
            (inversée par rapport au GPIO physique)
        """
        if x is None:
            # Lecture : inverser la valeur du GPIO
            return 1 - self._pin.value()
        else:
            # Écriture : inverser avant d'écrire
            self._pin.value(1 - x)

    def __call__(self, x=None):
        """
        Permet d'utiliser pin() comme pin.value()
        Compatible avec l'API Pin de MicroPython
        """
        return self.value(x)

    def on(self):
        """Active la sortie (GPIO LOW pour active-low)"""
        self._pin.value(0)

    def off(self):
        """Désactive la sortie (GPIO HIGH pour active-low)"""
        self._pin.value(1)

    def toggle(self):
        """Inverse l'état de la pin"""
        self._pin.toggle()

    def irq(self, handler=None, trigger=None, hard=False):
        """
        Configure une interruption sur la pin

        ATTENTION: Les triggers sont inversés en mode active-low !
        - IRQ_FALLING sur la pin logique = IRQ_RISING sur le GPIO physique
        - IRQ_RISING sur la pin logique = IRQ_FALLING sur le GPIO physique

        Args:
            handler: Fonction appelée lors de l'interruption
            trigger: Type de déclenchement (inversé automatiquement)
            hard: Non utilisé (pour compatibilité)

        Returns:
            Un objet callback
        """
        if trigger is not None:
            # Inverser les triggers pour le mode active-low
            inverted_trigger = 0
            if trigger & self.IRQ_FALLING:
                inverted_trigger |= self.IRQ_RISING
            if trigger & self.IRQ_RISING:
                inverted_trigger |= self.IRQ_FALLING
            trigger = inverted_trigger

        # Wrapper pour inverser la valeur passée au handler
        if handler is not None:
            def wrapper(pin):
                # Le handler reçoit cette instance (active-low)
                # avec la valeur logique déjà inversée
                handler(self)

            # Enregistrer sur la pin sous-jacente
            self._pin.irq(handler=wrapper, trigger=trigger, hard=hard)

        return self

    def mode(self, mode=None):
        """
        Obtient ou définit le mode de la pin

        Args:
            mode: Nouveau mode (IN ou OUT), ou None pour lire

        Returns:
            Le mode actuel si mode est None
        """
        return self._pin.mode(mode)

    def pull(self, pull=None):
        """
        Obtient ou définit la configuration du pull-up

        Args:
            pull: Nouvelle configuration (PULL_UP ou -1), ou None pour lire

        Returns:
            La configuration actuelle si pull est None
        """
        return self._pin.pull(pull)

    @property
    def pin_number(self):
        """Retourne le numéro du GPIO"""
        return self._pin._pin_number

    def __str__(self):
        """Représentation textuelle de la pin"""
        mode_str = "OUT" if self._pin._mode == self.OUT else "IN"
        pull_str = " PULL_UP" if self._pin._pull == self.PULL_UP else ""
        return f"MCP23009ActiveLowPin({self.pin_number}, {mode_str}{pull_str})"

    def __repr__(self):
        """Représentation pour le REPL"""
        return self.__str__()
