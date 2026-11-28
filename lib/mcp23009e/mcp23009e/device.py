from time import sleep_ms

from machine import Pin

from mcp23009e.const import (
    MCP23009_DEFVAL,
    MCP23009_DIR_INPUT,
    MCP23009_GPINTEN,
    MCP23009_GPIO,
    MCP23009_GPPU,
    MCP23009_INTCAP,
    MCP23009_INTCON,
    MCP23009_INTF,
    MCP23009_IOCON,
    MCP23009_IODIR,
    MCP23009_IPOL,
    MCP23009_LOGIC_HIGH,
    MCP23009_LOGIC_LOW,
    MCP23009_NO_PULLUP,
    MCP23009_OLAT,
    MCP23009_POL_SAME,
    MCP23009Config,
)


def _set_bit(reg, bit, value):
    """Modifie un bit spécifique dans un registre"""
    if value == 0:
        reg &= ~(1 << bit)
    else:
        reg |= (1 << bit)
    return reg


# Lectures d'interruption en attente de transmission : file circulaire de
# _QUEUE_LEN enregistrements de _RECORD mots, plus un emplacement de rebut
# (indice _QUEUE_LEN) écrit quand la file est pleine
_QUEUE_LEN = 8
_RECORD = 5


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

        # GPIO dont l'interruption est activée (un bit par GPIO), et dernier
        # niveau connu de chacun : celui du dernier événement transmis, ou
        # celui lu à l'activation
        self._enabled = 0
        self._levels = 0

        # Lectures d'interruption dont les événements restent à transmettre,
        # dans l'ordre : pour chacune, GPIO à transmettre depuis INTCAP, INTCAP,
        # GPIO à transmettre depuis GPIO, GPIO, et numéro d'enregistrement.
        # Indices de tête et de queue modulo 2 * _QUEUE_LEN. Tout est alloué
        # ici : le chemin d'interruption n'alloue rien.
        self._queue = [0] * (_RECORD * (_QUEUE_LEN + 1))
        self._head = 0
        self._tail = 0
        self._dispatching = False
        # 1 si une lecture n'a pas trouvé de place dans la file
        self._overflow = 0
        # Compteur des enregistrements de callbacks, et valeur de ce compteur
        # au dernier enregistrement de chaque GPIO : une lecture antérieure
        # n'appelle pas le nouveau callback
        self._generation = 0
        self._registered = [0] * 8

        # Configuration du pin de reset
        self.reset_pin.init(Pin.OUT)

        # Configuration du pin d'interruption si fourni
        if self.interrupt_pin is not None:
            self.interrupt_pin.init(Pin.IN)
            self.interrupt_pin.irq(trigger=Pin.IRQ_FALLING, handler=self._irq_handler)

        # Réinitialisation hardware
        self.reset()

    def reset(self):
        """
        Effectue un reset hardware du MCP23009E

        Le reset désactive les interruptions du composant : les callbacks
        doivent être enregistrés à nouveau.
        """
        self._enabled = 0
        self.reset_pin.value(0)
        sleep_ms(5)
        self.reset_pin.value(1)
        sleep_ms(10)

    def power_off(self):
        """
        Maintient le MCP23009E en reset

        Les interruptions du composant sont désactivées : les callbacks
        doivent être enregistrés à nouveau après power_on().
        """
        self._enabled = 0
        self.reset_pin.value(0)

    def power_on(self):
        self.reset_pin.value(1)
        sleep_ms(10)

    def _soft_reset(self):
        """
        Réinitialise le composant avec les valeurs par défaut

        Les interruptions sont désactivées : les callbacks doivent être
        enregistrés à nouveau.
        """
        self._enabled = 0
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

        Le callback doit déjà être enregistré : une interruption qui arrive
        dès l'écriture de GPINTEN le trouve. Avant cette écriture,
        l'interruption en attente est lue et effacée, pour qu'un changement
        antérieur à l'enregistrement n'appelle pas le nouveau callback. Le
        niveau lu à ce moment devient le dernier niveau connu du GPIO, sans
        événement, et les événements de ce GPIO encore en file sont
        abandonnés. Les événements en attente des autres GPIO sont transmis
        à leurs callbacks, pas perdus.

        Args:
            gpx: Numéro de GPIO (0 à 7)
        """
        # MicroPython n'exécute les IRQ logicielles qu'aux sauts (if, boucle,
        # and, or) : il n'y en a aucun dans cette méthode avant
        # _dispatch_queued(). Chaque lecture-modification-écriture de
        # registre est donc atomique, et une IRQ logicielle qui suit compare
        # gpx avec le niveau lu ici et transmet ses changements ultérieurs.
        # INTCON d'abord, bit à 0 = comparer avec l'état précédent : en mode
        # DEFVAL, activer GPINTEN déclencherait une interruption tout de suite
        self._write_reg(MCP23009_INTCON, self._read_reg(MCP23009_INTCON) & ~(1 << gpx))

        # Les lectures déjà en file ne transmettent plus d'événement de gpx
        self._generation += 1
        self._registered[gpx] = self._generation
        self._enabled |= 1 << gpx

        # Effacer l'interruption en attente, sans événement de gpx, et prendre
        # le niveau actuel de gpx comme dernier niveau connu
        self._read_interrupt(1 << gpx)
        self._write_reg(MCP23009_GPINTEN, self._read_reg(MCP23009_GPINTEN) | (1 << gpx))

        # Puis transmettre les événements des autres GPIO
        self._dispatch_queued()

    def _send_disable_interrupt(self, gpx):
        """
        Désactive l'interruption pour un GPIO spécifique

        Args:
            gpx: Numéro de GPIO (0 à 7)
        """
        # Clear the gpx bit of GPINTEN, INTCON (previous state) and DEFVAL
        # (low). Each read-modify-write has no jump between its read and its
        # write, so a scheduled soft IRQ cannot run in between.
        mask = ~(1 << gpx)
        # No event of gpx from now on, even one found in GPIO.
        self._enabled &= mask
        self._write_reg(MCP23009_GPINTEN, self._read_reg(MCP23009_GPINTEN) & mask)
        self._write_reg(MCP23009_INTCON, self._read_reg(MCP23009_INTCON) & mask)
        self._write_reg(MCP23009_DEFVAL, self._read_reg(MCP23009_DEFVAL) & mask)

    def interrupt_on_change(self, gpx, callback):
        """
        Active et enregistre un callback pour les changements d'état d'un GPIO

        Args:
            gpx: Numéro de GPIO (0 à 7)
            callback: Fonction appelée lors d'un changement (reçoit en paramètre
                le niveau de l'événement : capturé dans INTCAP, ou lu dans
                GPIO pour un changement que le composant n'a pas signalé)
        """
        if gpx > 7:
            return

        self.events_change[gpx] = callback
        self._send_enable_interrupt(gpx)

    def interrupt_on_falling(self, gpx, callback):
        """
        Active et enregistre un callback pour les fronts descendants d'un GPIO

        Args:
            gpx: Numéro de GPIO (0 à 7)
            callback: Fonction appelée lors d'un front descendant (pas de paramètre)
        """
        if gpx > 7:
            return

        self.events_fall[gpx] = callback
        self._send_enable_interrupt(gpx)

    def interrupt_on_rising(self, gpx, callback):
        """
        Active et enregistre un callback pour les fronts montants d'un GPIO

        Args:
            gpx: Numéro de GPIO (0 à 7)
            callback: Fonction appelée lors d'un front montant (pas de paramètre)
        """
        if gpx > 7:
            return

        self.events_rise[gpx] = callback
        self._send_enable_interrupt(gpx)

    # Deprecated: old spelling, kept for the whole 1.x series and removed in
    # 2.0.0. Same as arduino-steami-lib interruptOnRaising().
    interrupt_on_raising = interrupt_on_rising

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

        Lit INTF, INTCAP (le niveau de chaque GPIO au moment de
        l'interruption), puis GPIO. L'interruption est effacée quel que soit
        IOCON.INTCC. Pour chaque GPIO dont l'interruption est activée, le
        driver garde le dernier niveau connu et transmet, dans l'ordre :

        - le niveau capturé (INTCAP), si le GPIO est dans INTF et que ce
          niveau diffère du dernier connu ;
        - le niveau actuel (GPIO), s'il diffère encore du dernier connu.

        Un appui bref, relâché avant cette lecture, donne donc l'appui puis
        le relâchement. Tant qu'une interruption est en attente, le
        MCP23009 ne signale pas les changements des autres GPIO, et la
        lecture qui l'efface les prend comme nouvelle référence : la lecture
        de GPIO les retrouve et les transmet. Un niveau capturé égal au
        dernier connu (changement déjà transmis) n'est pas transmis deux
        fois.

        Les événements sont transmis dans l'ordre des lectures, un callback
        après l'autre. Une lecture faite pendant qu'un callback s'exécute
        (IRQ logicielle, ou callback qui enregistre une interruption) met
        ses événements en file : ils sont transmis après ceux des lectures
        précédentes. La file contient 8 lectures ; au-delà, les changements
        sont relus dans GPIO une fois la file vidée (les fronts
        intermédiaires sont alors perdus, le dernier niveau transmis reste
        juste). Si un callback lève une exception, les autres événements
        sont transmis quand même, puis la première exception est levée à
        nouveau.

        Limite : un appui et son relâchement survenus tous deux pendant
        qu'une interruption est en attente (entre la capture et cette
        lecture) s'annulent et restent invisibles.
        """
        self._read_interrupt(0)
        self._dispatch_queued()

    def _read_interrupt(self, skip_mask):
        """
        Lit et efface l'interruption en attente, et met ses événements en file

        Args:
            skip_mask: masque des GPIO dont l'événement est ignoré ; leur
                niveau actuel devient leur dernier niveau connu
        """
        # Lire INTF, puis INTCAP (niveau des GPIO capturé au moment de
        # l'interruption), puis GPIO. Selon IOCON.INTCC, la lecture de
        # INTCAP ou celle de GPIO efface l'interruption : lire les deux
        # l'efface dans tous les cas. MicroPython n'exécute les IRQ
        # logicielles qu'aux sauts (if, boucle, and, or) : cette méthode
        # n'en a aucun, pour qu'une IRQ logicielle ne traite pas une seconde
        # fois l'événement lu ici, ne compare pas avec des niveaux périmés,
        # ni ne mette ses événements en file avant ceux-ci.
        intf = self._read_reg(MCP23009_INTF)
        captured = self._read_reg(MCP23009_INTCAP)
        gpio = self._read_reg(MCP23009_GPIO)

        enabled = self._enabled & ~skip_mask
        last = self._levels
        # GPIO dans INTF dont le niveau capturé diffère du dernier connu
        from_intcap = intf & enabled & (captured ^ last)
        # GPIO dont le niveau actuel diffère encore (après from_intcap) :
        # changements après la capture, ou que le composant n'a pas signalés
        from_gpio = enabled & (gpio ^ last ^ from_intcap)

        # File pleine (tail - head == _QUEUE_LEN) : full = 1, sinon 0, calculé
        # sans saut. Si elle est pleine, l'enregistrement va à l'emplacement
        # de rebut, et les GPIO activés gardent leur dernier niveau connu :
        # une nouvelle lecture, une fois la file vidée, retrouve leurs
        # changements dans GPIO.
        tail = self._tail
        full = ((tail - self._head) & (2 * _QUEUE_LEN - 1)) // _QUEUE_LEN
        kept = full - 1  # 0 si la file est pleine, -1 (tous les bits) sinon
        tracked = skip_mask | (enabled & kept)
        self._overflow |= full
        self._levels = (last & ~tracked) | (gpio & tracked)

        slot = _RECORD * ((tail % _QUEUE_LEN) * (1 - full) + _QUEUE_LEN * full)
        queue = self._queue
        queue[slot] = from_intcap
        queue[slot + 1] = captured
        queue[slot + 2] = from_gpio
        queue[slot + 3] = gpio
        queue[slot + 4] = self._generation
        self._tail = (tail + 1 - full) % (2 * _QUEUE_LEN)

    def _dispatch_queued(self):
        """
        Transmet aux callbacks les événements en file, dans l'ordre

        Un seul appel transmet à la fois : un appel fait pendant un callback
        (IRQ logicielle, ou callback qui enregistre une interruption) revient
        tout de suite, et ses événements sont transmis par l'appel en cours,
        après ceux qui les précèdent.

        Un callback qui lève une exception n'arrête pas la transmission :
        les événements restants, y compris ceux mis en file entre-temps,
        sont transmis, puis la première exception est levée à nouveau.
        """
        error = None
        while not self._dispatching and (self._head != self._tail or self._overflow):
            self._dispatching = True
            try:
                # Une IRQ logicielle a pu vider la file juste avant que
                # _dispatching ne passe à True
                head = self._head
                if head != self._tail:
                    queue = self._queue
                    slot = _RECORD * (head % _QUEUE_LEN)
                    from_intcap = queue[slot]
                    captured = queue[slot + 1]
                    from_gpio = queue[slot + 2]
                    gpio = queue[slot + 3]
                    generation = queue[slot + 4]
                    self._head = (head + 1) % (2 * _QUEUE_LEN)
                    # Les niveaux capturés précèdent les niveaux actuels
                    for i in range(8):
                        if (from_intcap >> i) & 1:
                            exc = self._dispatch_if_current(i, (captured >> i) & 1, generation)
                            if error is None:
                                error = exc
                    for i in range(8):
                        if (from_gpio >> i) & 1:
                            exc = self._dispatch_if_current(i, (gpio >> i) & 1, generation)
                            if error is None:
                                error = exc
                elif self._overflow:
                    # File vidée après un débordement : relire les
                    # changements qui n'y ont pas trouvé de place
                    self._overflow = 0
                    self._read_interrupt(0)
            finally:
                self._dispatching = False
        if error is not None:
            raise error

    def _dispatch_if_current(self, i, level, generation):
        """
        Appelle les callbacks du GPIO i, sauf si son interruption a été
        désactivée, ou enregistrée à nouveau, après la lecture de l'événement

        Returns:
            La première exception levée par un callback, ou None
        """
        if (self._enabled >> i) & 1 and generation >= self._registered[i]:
            return self._dispatch(i, level)
        return None

    def _dispatch(self, i, level):
        """
        Appelle les callbacks du GPIO i pour un événement de niveau level

        Une exception levée par un callback n'empêche pas l'appel du suivant.

        Returns:
            La première exception levée par un callback, ou None
        """
        error = None
        callback = self.events_rise[i] if level == MCP23009_LOGIC_HIGH else self.events_fall[i]
        if callback is not None:
            try:
                callback()
            except Exception as exc:
                error = exc

        # Appeler le callback de changement avec le niveau
        callback = self.events_change[i]
        if callback is not None:
            try:
                callback(level)
            except Exception as exc:
                if error is None:
                    error = exc
        return error
