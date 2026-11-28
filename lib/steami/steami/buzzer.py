"""Buzzer: tone() and no_tone(), as Arduino tone() and noTone().

The buzzer is on SPEAKER (PA11), driven by hardware PWM on Timer 1 channel 4.
The timer is created on first use. A timed tone stops by itself through a
one-shot soft timer, so tone() never blocks.
"""

_timer = None
_channel = None
_stop = None


def _cancel():
    global _stop
    if _stop is not None:
        _stop.deinit()
        _stop = None


def no_tone():
    """Silence the buzzer and cancel a pending timed stop."""
    _cancel()
    if _channel is not None:
        _channel.pulse_width_percent(0)


def tone(frequency, duration_ms=0):
    """Play a square wave of frequency Hz on the buzzer.

    With duration_ms > 0, the tone stops by itself after that time, without
    blocking. A frequency of 0 or less silences the buzzer.
    """
    global _timer, _channel, _stop
    if frequency <= 0:
        no_tone()
        return
    _cancel()
    if _timer is None:
        from pyb import Pin, Timer

        _timer = Timer(1, freq=frequency)
        _channel = _timer.channel(4, Timer.PWM, pin=Pin("SPEAKER"))
    else:
        _timer.freq(frequency)
    _channel.pulse_width_percent(50)
    if duration_ms > 0:
        from machine import Timer

        _stop = Timer(-1, mode=Timer.ONE_SHOT, period=duration_ms, callback=lambda t: no_tone())
