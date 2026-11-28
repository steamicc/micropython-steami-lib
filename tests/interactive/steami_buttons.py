"""Interactive check of steami.Buttons on a STeaMi V1c: taps caught between two slow calls.

REQUIRES A HUMAN. The same scenario as tests/integration/test_steami_buttons
of arduino-steami-lib (issues steamicc/arduino-steami-lib#341 and #515 here):
same buttons, same loops, same counts. Each step prints its instruction to the
serial output and shows it, in French, on the screen: a 3-2-1 countdown, then
"À vous !". No LED is lit. The whole run takes about eight minutes.

Run it with lib/ mounted, so that the steami and mcp23009e sources of this
checkout are used instead of the frozen ones:

    make test-interactive-buttons PORT=/dev/ttyACM0
    make test-interactive-buttons PORT=/dev/ttyACM0 STEP=14   # one step alone

(that is: python -m mpremote connect PORT mount lib exec "STEP = 14"
run tests/interactive/steami_buttons.py). Nothing else may be connected on
P1, P2, P7, P10, P12 or Jacdac.

- Step 1: an IRQ the program sets on MENU_BUTTON fires beside the expander
  (which takes no EXTI line).
- Step 2: registering the four D-pad callbacks five times gives no event.
- Step 3: the EXTI lines of A, B and MENU are routed to their pins, unmasked
  on both edges, with their NVIC interrupt enabled: before the screen starts,
  after it started, and after a redraw.
- Steps 4 to 10: ten quick taps on each of the seven buttons, about one per
  second, in a fixed window of 15 s, with a loop that calls the buttons every
  300 ms: get_presses() counts exactly ten on that button and none on the
  others. The window does not stop at ten. For A, B and MENU, a 1 kHz timer
  that reads the pin counts the taps on its own ("au doigt").
- Steps 11 and 12: the same on A and on B, two or three taps per second,
  faster than the loop: get_presses() must still count ten.
- Step 13: D-pad reference, ten taps on UP about once per second, counted by
  reading the port of the expander every 2 ms (no Buttons object).
- Step 14: ten taps on UP with the 520 ms loop of the second hardware run
  (4 UP out of 10 before the fix), one at each number of a metronome on the
  screen, every 700 ms: more than one turn of the loop between two taps, so
  get_presses() must count ten, and less than two, where the old D-pad
  release merged them. Not two or three per second, as the Arduino step 14
  asks: with a 520 ms loop, two D-pad taps then often fall between two reads
  of the expander, and the chip latches the first change only (a limit of the
  MCP23009, not of Buttons).
- Steps 15 and 16: ten holds of two seconds on A, then on UP: ten presses and
  ten releases, each held more than one second, is_pressed() true at every
  call in between.
- Step 17: 60 s of fast presses on the D-pad, read by interrupt_event()
  every 30 ms: the levels the driver reports alternate on each pin.

The screen is redrawn only when what it shows changes, and the time of the
redraw comes off the wait: the loop keeps its period.
"""

import os
import sys

if "remote" in os.listdir("/"):
    # The sources of this checkout first; '' (the mounted lib/) would make a
    # bare driver folder hide the frozen package of the same name.
    sys.path[:] = ["/remote/steami", "/remote/mcp23009e"] + [
        p for p in sys.path if p not in ("", ".", "/remote")
    ]

from time import sleep_ms, ticks_add, ticks_diff, ticks_ms

from machine import Pin, mem32
from mcp23009e.const import (
    MCP23009_BTN_DOWN,
    MCP23009_BTN_LEFT,
    MCP23009_BTN_RIGHT,
    MCP23009_BTN_UP,
    MCP23009_DIR_INPUT,
    MCP23009_PULLUP,
)
from steami import Buttons, Screen, Steami
from steami_screen import GREEN, LIGHT, RED, WHITE, YELLOW

STEP = globals().get("STEP", 0)  # 0: every step

LOOP_MS = 300
SLOW_LOOP_MS = 520
BEAT_MS = 700  # metronome of step 14: between one and two turns of SLOW_LOOP_MS
REF_POLL_MS = 2
TAPS = 10
TAP_WINDOW_MS = 15000
PROMPT_TIMEOUT_MS = 5000
LONG_PRESS_MS = 1000  # the hold asked is two seconds
LONG_WINDOW_MS = 60000
STORM_MS = 60000
RESULT_MS = 2000
STEPS = 17

NAMES = ("A", "B", "MENU", "UP", "DOWN", "LEFT", "RIGHT")
FRENCH = ("A", "B", "MENU", "HAUT", "BAS", "GAUCHE", "DROITE")
PINS = ("A_BUTTON", "B_BUTTON", "MENU_BUTTON")
DPAD_BITS = (MCP23009_BTN_UP, MCP23009_BTN_DOWN, MCP23009_BTN_LEFT, MCP23009_BTN_RIGHT)

# STM32WB55 registers (RM0434).
SYSCFG_EXTICR = 0x40010008
EXTI_RTSR1 = 0x58000800
EXTI_FTSR1 = 0x58000804
EXTI_IMR1 = 0x58000880
NVIC_ISER = 0xE000E100

screen = Screen()
step = 0
results = []  # (step, name, failures)
failures = []


def check(ok, message):
    if not ok:
        failures.append(message)
        print("  FAIL:", message)


# --- Screen: the French instructions ---


def head():
    return "Épreuve {}/{}".format(step, STEPS)


def show(word, l1, l2=None, color=LIGHT):
    screen.clear()
    screen.title(head())
    screen.text(word, "CENTER", color, 2)
    screen.subtitle(*[line for line in (l1, l2) if line], color=WHITE)
    screen.show()


def prompt(text, l1, l2):
    print(text)
    for n in (3, 2, 1):
        t0 = ticks_ms()
        screen.clear()
        screen.title(head())
        screen.value(n, color=YELLOW, scale=3)
        screen.subtitle(l1, l2, color=LIGHT)
        screen.show()
        wait_rest(t0, 1000)
    show("À vous !", l1, l2, GREEN)


def wait_rest(turn, period):
    spent = ticks_diff(ticks_ms(), turn)
    if spent < period:
        sleep_ms(period - spent)


def result(good, l1, l2):
    show("OK" if good else "Écart", l1, l2, GREEN if good else RED)
    sleep_ms(RESULT_MS)


# --- Reference: the taps seen by a 1 kHz timer on the pin of A, B or MENU ---
#
# A 10 ms stable level changes the state; a change to pressed counts a tap.
# Independent of Buttons and of the EXTI. Hard IRQ: no allocation.

_ref = [False, 0, False, 0]  # raw level, stable samples, state, taps
_ref_pin = None
_ref_timer = None


def _ref_sample(_timer):
    r = _ref
    down = _ref_pin.value() == 0
    if down != r[0]:
        r[0] = down
        r[1] = 0
    elif r[1] < 10:
        r[1] += 1
    elif down != r[2]:
        r[2] = down
        if down:
            r[3] += 1


def ref_start(name):
    global _ref_pin, _ref_timer
    _ref_pin = Pin(name)
    down = _ref_pin.value() == 0
    _ref[0] = _ref[2] = down
    _ref[1] = 10
    _ref[3] = 0
    try:
        import pyb  # stm32 port only

        _ref_timer = pyb.Timer(2, freq=1000, callback=_ref_sample)
    except Exception as e:
        _ref_timer = None
        print("  1 kHz reference not available:", e)


def ref_stop():
    if _ref_timer is None:
        return None
    _ref_timer.deinit()
    return _ref[3]


# --- EXTI lines of A, B and MENU ---


def exti_armed(label):
    # The EXTI line of each pin is routed to its port, unmasked on both edges,
    # and its NVIC interrupt is enabled. A line turned off or taken by another
    # port leaves that button sampled at each call only.
    armed = True
    for name, pin_name in zip(NAMES, PINS):
        pin = Pin(pin_name)
        line = pin.pin()
        port = pin.port()
        mask = 1 << line
        routed = (mem32[SYSCFG_EXTICR + 4 * (line >> 2)] >> ((line & 3) * 4)) & 7
        imr = (mem32[EXTI_IMR1] & mask) != 0
        rising = (mem32[EXTI_RTSR1] & mask) != 0
        falling = (mem32[EXTI_FTSR1] & mask) != 0
        irq = 6 + line if line < 5 else (23 if line < 10 else 40)
        nvic = (mem32[NVIC_ISER + 4 * (irq >> 5)] >> (irq & 31)) & 1
        print(
            "  {} ({}): EXTI line {}, port {} routed {}, IMR {}, rising {}, falling {}, "
            "NVIC {}".format(name, label, line, port, routed, imr, rising, falling, nvic)
        )
        armed = armed and routed == port and imr and rising and falling and nvic == 1
    return armed


# --- Steps ---


def step_menu_irq_survives_the_expander():
    fired = [False]

    def on_menu(_pin):
        fired[0] = True

    menu = Pin("MENU_BUTTON", Pin.IN, Pin.PULL_UP)
    menu.irq(on_menu, Pin.IRQ_FALLING)
    check(Steami.mcp23009e() is not None, "no expander")
    prompt("Press MENU once.", "MENU : 1 seul appui", "dans les 5 s")
    start = ticks_ms()
    while not fired[0] and ticks_diff(ticks_ms(), start) < PROMPT_TIMEOUT_MS:
        sleep_ms(10)
    menu.irq(None)
    check(fired[0], "the MENU_BUTTON IRQ did not fire")


def step_dpad_registration_gives_no_event():
    show("Attendez", "Ne touchez à rien")
    expander = Steami.mcp23009e()
    events = [0]

    def on_change(_level):
        events[0] += 1

    for _ in range(5):
        for bit in DPAD_BITS:
            expander.setup(bit, MCP23009_DIR_INPUT, MCP23009_PULLUP)
            expander.interrupt_on_change(bit, on_change)
        expander.interrupt_event()
    for bit in DPAD_BITS:
        expander.disable_interrupt(bit)
    check(events[0] == 0, "{} event(s) with no button touched".format(events[0]))


def step_exti_lines_are_armed():
    show("Attendez", "Ne touchez à rien")
    check(EXTI_AT_START[0], "EXTI not armed before the screen started")
    check(EXTI_AT_START[1], "EXTI not armed after the screen started")
    buttons = Buttons()
    check(buttons.begin(), "Buttons.begin() failed")
    check(not buttons.is_pressed("A"), "A pressed")
    check(exti_armed("new Buttons"), "EXTI not armed after Buttons.begin()")
    show("Attendez", "Ne touchez à rien", "écran redessiné")
    check(not buttons.is_pressed("A"), "A pressed")
    check(exti_armed("after a redraw"), "EXTI not armed after a redraw")


def draw_taps(title, seen, left):
    screen.clear()
    screen.title(title)
    screen.value(seen, "tapes vues", color=WHITE)
    screen.subtitle("objectif : {}".format(TAPS), "reste {} s".format(left), color=LIGHT)
    screen.show()


def draw_beat(title, beat, seen):
    screen.clear()
    screen.title(title)
    if beat <= TAPS:
        screen.value(beat, "tapez au top", color=YELLOW)
    else:
        screen.text("Fin", "CENTER", LIGHT, 2)
    screen.subtitle("tapes vues : {}".format(seen), color=LIGHT)
    screen.show()


def count_taps_on(target, loop_ms=LOOP_MS, fast=False, beat_ms=0):
    # beat_ms: a metronome on the screen, one tap at each new number.
    buttons = Buttons()
    check(buttons.begin(), "Buttons.begin() failed")
    mcu = target < 3
    name = NAMES[target]
    if beat_ms:
        pace = "one at each new number on the screen (every {} ms)".format(beat_ms)
        hint = "une à chaque top"
        window = (TAPS + 2) * beat_ms
    else:
        pace = "two or three times per second" if fast else "about once per second"
        hint = "2 à 3 par seconde" if fast else "une par seconde"
        window = TAP_WINDOW_MS
    text = (
        "Tap {} exactly {} times, quickly (under 150 ms), {}, within {} s. Touch nothing "
        "else. The loop calls the buttons every {} ms.".format(
            name, TAPS, pace, window // 1000, loop_ms
        )
    )
    title = "{} : {} tapes brèves".format(FRENCH[target], TAPS)
    prompt(text, title, hint)
    for n in NAMES:  # what was pressed during the countdown does not count
        buttons.get_presses(n)
        buttons.was_pressed(n)
        buttons.was_released(n)
    if mcu:
        ref_start(PINS[target])
    presses = [0] * 7
    releases = [0] * 7
    shown = None
    start = ticks_ms()
    while ticks_diff(ticks_ms(), start) < window:
        turn = ticks_ms()
        for k, n in enumerate(NAMES):
            presses[k] += buttons.get_presses(n)
            releases[k] += buttons.was_released(n)
        elapsed = ticks_diff(ticks_ms(), start)
        if beat_ms:
            beat = elapsed // beat_ms + 1
            if beat != shown:
                shown = beat
                draw_beat(title, beat, presses[target])
        else:
            left = max(0, (window - elapsed + 999) // 1000)
            if (presses[target], left) != shown:
                shown = (presses[target], left)
                draw_taps(title, presses[target], left)
        wait_rest(turn, loop_ms)
    for k, n in enumerate(NAMES):  # the last turn
        presses[k] += buttons.get_presses(n)
        releases[k] += buttons.was_released(n)
    finger = ref_stop() if mcu else None
    # was_released() is a flag: the turns that saw two releases count one.
    for k, n in enumerate(NAMES):
        print(
            "  {}: {} presses (get_presses), {} turns with a release".format(
                n, presses[k], releases[k]
            )
        )
    if finger is not None:
        print("  {}: {} taps seen by the 1 kHz reference".format(name, finger))
    good = presses[target] == TAPS and finger in (None, TAPS)
    result(
        good,
        "tapes vues : {}".format(presses[target]),
        "au doigt : {}".format(finger) if finger is not None else "attendu : {}".format(TAPS),
    )
    if mcu:
        check(exti_armed("after the window"), "EXTI not armed after the window")
        check(
            finger in (None, presses[target]),
            "presses reported differ from the taps of the reference",
        )
    check(
        presses[target] == TAPS,
        "{} presses of {}, {} expected".format(presses[target], name, TAPS),
    )
    check(1 <= releases[target] <= TAPS, "turns with a release of {}".format(name))
    for k, n in enumerate(NAMES):
        if k != target:
            check(presses[k] == 0, "{} press(es) on {}, nobody touched it".format(presses[k], n))
    check(not buttons.is_pressed(name), "{} still pressed".format(name))


def step_dpad_reference_taps_on_up():
    expander = Steami.mcp23009e()
    for bit in DPAD_BITS:
        expander.setup(bit, MCP23009_DIR_INPUT, MCP23009_PULLUP)
    prompt(
        "Reference: tap UP exactly {} times, quickly, about once per second, within {} s. "
        "Touch nothing else.".format(TAPS, TAP_WINDOW_MS // 1000),
        "HAUT : 10 tapes (réf.)",
        "une par seconde",
    )
    port = expander.get_gpio()
    raw = [not port & (1 << bit) for bit in DPAD_BITS]
    down = list(raw)
    stable = [0] * 4
    taps = [0] * 4
    errors = 0
    stable_reads = 10 // REF_POLL_MS
    start = ticks_ms()
    deadline = start
    while ticks_diff(ticks_ms(), start) < TAP_WINDOW_MS:
        early = ticks_diff(deadline, ticks_ms())
        if early > 0:
            sleep_ms(early)
        deadline = ticks_add(deadline, REF_POLL_MS)
        try:
            port = expander.get_gpio()
        except OSError:
            errors += 1
            continue
        for d, bit in enumerate(DPAD_BITS):
            now = not port & (1 << bit)
            if now != raw[d]:
                raw[d] = now
                stable[d] = 0
            elif stable[d] < stable_reads:
                stable[d] += 1
            elif now != down[d]:
                down[d] = now
                taps[d] += now
    for d in range(4):
        print(
            "  {}: {} taps seen by reading the expander every {} ms".format(
                NAMES[3 + d], taps[d], REF_POLL_MS
            )
        )
    good = taps[0] == TAPS and sum(taps[1:]) == 0 and errors == 0
    result(good, "au doigt : {}".format(taps[0]), "attendu : {}".format(TAPS))
    check(errors == 0, "{} expander read(s) failed".format(errors))
    check(taps[0] == TAPS, "{} taps on UP seen by the reference".format(taps[0]))
    check(sum(taps[1:]) == 0, "taps on the other arrows")


def draw_hold(title, presses, holding, held_s):
    screen.clear()
    screen.title(title)
    screen.value(presses, "appuis", color=WHITE)
    screen.subtitle(
        "objectif : {}".format(TAPS),
        "maintenu {} s".format(held_s) if holding else "relâché",
        color=GREEN if holding else LIGHT,
    )
    screen.show()


def count_long_presses_on(target):
    # The hold is measured between the call that reports the press and the
    # one that reports the release: one turn of the loop of error at most, so
    # a hold of two seconds is far above one. is_pressed() must be true at
    # every call in between.
    buttons = Buttons()
    check(buttons.begin(), "Buttons.begin() failed")
    name = NAMES[target]
    title = "{} : {} appuis longs".format(FRENCH[target], TAPS)
    prompt(
        "Press and hold {} for two seconds (the screen counts them), {} times, with a "
        "pause between two.".format(name, TAPS),
        title,
        "2 s chacun",
    )
    while buttons.was_pressed(name):
        pass
    while buttons.was_released(name):
        pass
    presses = releases = held_long = drops = 0
    holding = False
    pressed_at = 0
    shown = None
    start = ticks_ms()
    while releases < TAPS and ticks_diff(ticks_ms(), start) < LONG_WINDOW_MS:
        turn = ticks_ms()
        if buttons.was_pressed(name):
            presses += 1
            holding = True
            pressed_at = ticks_ms()
        down = buttons.is_pressed(name)
        if buttons.was_released(name):
            releases += 1
            if holding and ticks_diff(ticks_ms(), pressed_at) >= LONG_PRESS_MS:
                held_long += 1
            holding = False
        elif holding and not down:
            drops += 1
        held_s = ticks_diff(ticks_ms(), pressed_at) // 1000 if holding else 0
        if (presses, holding, held_s) != shown:
            shown = (presses, holding, held_s)
            draw_hold(title, presses, holding, held_s)
        wait_rest(turn, LOOP_MS)
    print(
        "  {}: {} presses, {} releases, {} held more than 1 s, {} calls not pressed "
        "while held".format(name, presses, releases, held_long, drops)
    )
    good = presses == releases == held_long == TAPS and drops == 0
    result(good, "tenus 1 s : {}".format(held_long), "coupures : {}".format(drops))
    check(drops == 0, "is_pressed() false while the button was held")
    check(presses == TAPS, "{} presses".format(presses))
    check(releases == TAPS, "{} releases".format(releases))
    check(held_long == TAPS, "{} presses held more than one second".format(held_long))


def step_dpad_levels_alternate_under_fast_presses():
    expander = Steami.mcp23009e()
    last = [-1] * 4
    events = [0] * 4
    alternate = [True]

    def watcher(d):
        def on_change(level):
            if last[d] == level:
                alternate[0] = False
            last[d] = level
            events[d] += 1

        return on_change

    for d, bit in enumerate(DPAD_BITS):
        expander.setup(bit, MCP23009_DIR_INPUT, MCP23009_PULLUP)
        expander.interrupt_on_change(bit, watcher(d))
    prompt(
        "For 60 s, press the four D-PAD buttons as fast as you can, together or not.",
        "D-PAD : 60 s",
        "le plus vite possible",
    )
    start = ticks_ms()
    while ticks_diff(ticks_ms(), start) < STORM_MS:
        expander.interrupt_event()  # no interrupt pin: reads the latch at each call
        sleep_ms(LOOP_MS // 10)
    print("Stop and release every button.")
    show("Stop", "Relâchez tout", None, YELLOW)
    sleep_ms(2000)
    expander.interrupt_event()
    for d in range(4):
        print("  {}: {} events".format(NAMES[3 + d], events[d]))
    for bit in DPAD_BITS:
        expander.disable_interrupt(bit)
    check(alternate[0], "two events in a row with the same level")
    for d, bit in enumerate(DPAD_BITS):
        if last[d] >= 0:
            check(
                expander.get_level(bit) == last[d], "last event level of {}".format(NAMES[3 + d])
            )


STEPS_RUN = (
    (1, "MENU IRQ survives the expander", step_menu_irq_survives_the_expander),
    (2, "D-pad registration gives no event", step_dpad_registration_gives_no_event),
    (3, "EXTI lines of A, B, MENU are armed", step_exti_lines_are_armed),
    (4, "quick taps on A", lambda: count_taps_on(0)),
    (5, "quick taps on B", lambda: count_taps_on(1)),
    (6, "quick taps on MENU", lambda: count_taps_on(2)),
    (7, "quick taps on UP", lambda: count_taps_on(3)),
    (8, "quick taps on DOWN", lambda: count_taps_on(4)),
    (9, "quick taps on LEFT", lambda: count_taps_on(5)),
    (10, "quick taps on RIGHT", lambda: count_taps_on(6)),
    (11, "fast taps on A", lambda: count_taps_on(0, fast=True)),
    (12, "fast taps on B", lambda: count_taps_on(1, fast=True)),
    (13, "D-pad reference: taps on UP", step_dpad_reference_taps_on_up),
    (14, "taps on UP with a 520 ms loop", lambda: count_taps_on(3, SLOW_LOOP_MS, beat_ms=BEAT_MS)),
    (15, "long presses on A", lambda: count_long_presses_on(0)),
    (16, "long presses on UP", lambda: count_long_presses_on(3)),
    (
        17,
        "D-pad levels alternate under fast presses",
        step_dpad_levels_alternate_under_fast_presses,
    ),
)

# The buttons first, then the screen, as in the Arduino test and in most
# programs: the EXTI lines are checked before and after the screen starts.
print("[steami_buttons] Board:", Steami.begin())
_boot = Buttons()
_boot.begin()
_boot.is_pressed("A")
EXTI_AT_START = [exti_armed("before the screen starts")]
screen.begin()
EXTI_AT_START.append(exti_armed("after the screen starts"))

for number, name, run in STEPS_RUN:
    if STEP and number != STEP:
        continue
    step = number
    failures = []
    print("\n=== Step {}/{}: {} ===".format(number, STEPS, name))
    try:
        run()
    except Exception as e:
        sys.print_exception(e)
        failures.append("exception: {!r}".format(e))
    print("  PASS" if not failures else "  FAIL ({})".format(len(failures)))
    results.append((number, name, failures))

print("\n=== Summary ===")
for number, name, fails in results:
    print(
        "{:>2} {:<44} {}".format(
            number, name, "PASS" if not fails else "FAIL: " + "; ".join(fails)
        )
    )
passed = sum(1 for r in results if not r[2])
print("{}/{} steps passed".format(passed, len(results)))
show(
    "Fin",
    "{}/{} réussies".format(passed, len(results)),
    None,
    GREEN if passed == len(results) else RED,
)
