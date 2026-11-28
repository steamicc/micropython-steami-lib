"""
Module fournissant une classe Pin compatible avec l'API MicroPython
pour les GPIO du MCP23009E
"""


from mcp23009e.const import (
    MCP23009_DIR_INPUT,
    MCP23009_DIR_OUTPUT,
    MCP23009_LOGIC_HIGH,
    MCP23009_LOGIC_LOW,
    MCP23009_NO_PULLUP,
    MCP23009_PULLUP,
)


class MCP23009Pin:
    """
    Classe émulant une Pin MicroPython pour les GPIO du MCP23009E

    Cette classe permet d'utiliser les GPIO de l'expandeur I/O MCP23009E
    de la même manière que les pins natives de MicroPython.

    Exemple:
        >>> from mcp23009e import MCP23009E
        >>> from mcp23009e.pin import MCP23009Pin
        >>> mcp = MCP23009E(i2c, address=0x20, reset_pin=reset)
        >>> led = MCP23009Pin(mcp, 0, MCP23009Pin.OUT)
        >>> led.value(1)  # Allume la LED
        >>> led.off()     # Éteint la LED
    """

    # Constantes de mode (compatibles avec machine.Pin)
    IN = MCP23009_DIR_INPUT
    OUT = MCP23009_DIR_OUTPUT

    # Constantes de pull (compatibles avec machine.Pin)
    PULL_UP = MCP23009_PULLUP

    # Constantes de déclenchement d'interruption (compatibles avec machine.Pin)
    IRQ_FALLING = 1
    IRQ_RISING = 2
    IRQ_LOW_LEVEL = 3
    IRQ_HIGH_LEVEL = 4

    def __init__(self, mcp, pin_number, mode=-1, pull=-1, value=None):
        """
        Initialise une pin virtuelle du MCP23009E

        Args:
            mcp: Instance de MCP23009E
            pin_number: Numéro du GPIO (0 à 7)
            mode: Mode de la pin (IN ou OUT), optionnel
            pull: Configuration du pull-up (PULL_UP ou -1), optionnel
            value: Valeur initiale si en mode OUT, optionnel
        """
        if pin_number < 0 or pin_number > 7:
            raise ValueError("Le numéro de pin doit être entre 0 et 7")

        self._mcp = mcp
        self._pin_number = pin_number
        self._mode = -1
        self._pull = -1
        self._irq_handler = None
        self._irq_trigger = None
        self._irq_level = None

        # Configuration initiale si des paramètres sont fournis
        if mode != -1:
            self.init(mode, pull, value)

    def init(self, mode=-1, pull=-1, value=None):
        """
        (Re)configure la pin

        Args:
            mode: Mode de la pin (IN ou OUT)
            pull: Configuration du pull-up (PULL_UP ou -1)
            value: Valeur initiale si en mode OUT
        """
        if mode != -1:
            self._mode = mode

        if pull != -1:
            self._pull = pull
        elif self._pull == -1:
            self._pull = MCP23009_NO_PULLUP

        # Appliquer la configuration sur le MCP23009E
        pullup = MCP23009_PULLUP if self._pull == self.PULL_UP else MCP23009_NO_PULLUP
        self._mcp.setup(self._pin_number, self._mode, pullup=pullup)

        # Si une valeur initiale est fournie et mode OUT, l'appliquer
        if value is not None and self._mode == self.OUT:
            self.value(value)

    def value(self, x=None):
        """
        Obtient ou définit la valeur de la pin

        Args:
            x: Nouvelle valeur (0 ou 1), ou None pour lire

        Returns:
            Si x est None, retourne la valeur actuelle (0 ou 1)
            Sinon, retourne None après avoir défini la valeur
        """
        if x is None:
            # Lecture
            return self._mcp.get_level(self._pin_number)
        else:
            # Écriture
            level = MCP23009_LOGIC_HIGH if x else MCP23009_LOGIC_LOW
            self._mcp.set_level(self._pin_number, level)

    def __call__(self, x=None):
        """
        Permet d'utiliser pin() comme pin.value()
        Compatible avec l'API Pin de MicroPython
        """
        return self.value(x)

    def on(self):
        """Met la pin à l'état haut (1)"""
        self.value(1)

    def off(self):
        """Met la pin à l'état bas (0)"""
        self.value(0)

    def toggle(self):
        """Inverse l'état de la pin"""
        self.value(1 - self.value())

    def irq(self, handler=None, trigger=IRQ_FALLING | IRQ_RISING, hard=False):
        """
        Configure une interruption sur la pin

        Le handler reçoit la pin, comme avec machine.Pin. Il s'exécute après
        coup (soft IRQ) : la broche a pu changer depuis l'interruption.
        Dans le handler, pin.irq_level() donne le niveau de l'événement
        (capturé au moment de l'interruption, ou lu dans GPIO pour un
        changement que le MCP23009 n'a pas signalé), et pin.value() le
        niveau actuel. Un appui bref donne deux événements : l'appui, puis
        le relâchement.

        L'enregistrement remplace le précédent, efface l'interruption en
        attente et prend le niveau actuel de la pin comme dernier niveau
        connu : un changement antérieur à l'appel de irq() n'appelle pas le
        handler, même s'il est encore en file pendant qu'un autre handler
        s'exécute.

        Args:
            handler: Fonction appelée lors de l'interruption (reçoit la pin en paramètre)
            trigger: Type de déclenchement (IRQ_FALLING, IRQ_RISING, ou les deux)
            hard: Non utilisé (pour compatibilité avec machine.Pin)

        Returns:
            Un objet callback (cette instance)

        Exemple:
            >>> def callback(pin):
            ...     print("appuyé" if pin.irq_level() == 0 else "relâché")
            >>> pin.irq(handler=callback, trigger=MCP23009Pin.IRQ_FALLING | MCP23009Pin.IRQ_RISING)
        """
        self._irq_handler = handler
        self._irq_trigger = trigger

        # Créer un wrapper qui note le niveau de l'événement, puis appelle le
        # handler avec self en paramètre
        def wrapper(level):
            self._irq_level = level
            if self._irq_handler is not None:
                self._irq_handler(self)

        # Retirer les callbacks d'un enregistrement précédent, qui peut avoir
        # utilisé un autre trigger
        self._mcp.events_change[self._pin_number] = None
        self._mcp.events_fall[self._pin_number] = None
        self._mcp.events_rise[self._pin_number] = None

        # Enregistrer les callbacks appropriés selon le trigger
        if trigger & self.IRQ_FALLING:
            if trigger & self.IRQ_RISING:
                # Les deux fronts : utiliser interrupt_on_change
                self._mcp.interrupt_on_change(self._pin_number, wrapper)
            else:
                # Seulement falling
                self._mcp.interrupt_on_falling(self._pin_number, lambda: wrapper(0))
        elif trigger & self.IRQ_RISING:
            # Seulement rising
            self._mcp.interrupt_on_rising(self._pin_number, lambda: wrapper(1))

        return self

    def irq_level(self):
        """
        Niveau de la pin pour l'événement en cours de traitement

        À lire dans le handler de irq() : c'est le niveau capturé au moment
        de l'interruption (registre INTCAP), même si la broche a changé
        avant que le handler ne s'exécute, ou le niveau lu dans GPIO pour
        un changement que le MCP23009 n'a pas signalé (survenu pendant
        qu'une autre interruption était en attente). pin.value(), lui,
        relit le niveau actuel.

        Returns:
            0 ou 1, ou None si aucune interruption n'a encore été reçue
        """
        return self._irq_level

    def mode(self, mode=None):
        """
        Obtient ou définit le mode de la pin

        Args:
            mode: Nouveau mode (IN ou OUT), ou None pour lire

        Returns:
            Le mode actuel si mode est None
        """
        if mode is None:
            return self._mode
        else:
            self.init(mode=mode, pull=self._pull)

    def pull(self, pull=None):
        """
        Obtient ou définit la configuration du pull-up

        Args:
            pull: Nouvelle configuration (PULL_UP ou -1), ou None pour lire

        Returns:
            La configuration actuelle si pull est None
        """
        if pull is None:
            return self._pull
        else:
            self.init(mode=self._mode, pull=pull)

    def __str__(self):
        """Représentation textuelle de la pin"""
        mode_str = "OUT" if self._mode == self.OUT else "IN"
        pull_str = " PULL_UP" if self._pull == self.PULL_UP else ""
        return f"MCP23009Pin({self._pin_number}, {mode_str}{pull_str})"

    def __repr__(self):
        """Représentation pour le REPL"""
        return self.__str__()
