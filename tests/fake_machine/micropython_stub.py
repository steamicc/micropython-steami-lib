"""Stub for the micropython module, so const() and the code emitters work on CPython.

native is an identity decorator: the function runs as plain Python. Viper
annotates pointer arguments with ptr8, ptr16 and ptr32, names the board
compiler resolves by itself; importing this stub defines them as builtins,
so the annotations evaluate on CPython.

On the board a ptr16 or ptr32 argument indexes native 16- or 32-bit words
(little-endian on the STM32), not bytes. viper therefore wraps each
argument annotated ptr16 or ptr32 in a word view over the same buffer
(_Words, little-endian, store truncated to the word size), and leaves
ptr8 arguments as they are (a bytearray already indexes bytes). A word
view reaches the bytes through the buffer's own indexing, so a guarded
buffer still sees every access, and it refuses an index outside the
buffer, where viper would read or write past it.

Not emulated: viper ints are signed 32-bit on the board (shifts and
overflow wrap, << 32 gives 0), while the stub runs them as unbounded
Python ints. Callers keep their values in range (for example
GC9A01Display packs dims only for a width below 32768).
"""

import builtins
import functools


def const(x):
    return x


def native(f):
    return f


class _Words:
    """A buffer seen as little-endian words of SIZE bytes, like a viper pointer."""

    SIZE = 2

    def __init__(self, buf):
        self._buf = buf
        self._len = len(buf) // self.SIZE

    def _base(self, i):
        if not 0 <= i < self._len:
            raise IndexError("viper pointer index {} outside {} words".format(i, self._len))
        return i * self.SIZE

    def __getitem__(self, i):
        base = self._base(i)
        buf = self._buf
        return sum(buf[base + k] << (8 * k) for k in range(self.SIZE))

    def __setitem__(self, i, v):
        base = self._base(i)
        buf = self._buf
        for k in range(self.SIZE):
            buf[base + k] = (v >> (8 * k)) & 0xFF


class ptr16(_Words):  # noqa: N801 (the viper name)
    SIZE = 2


class ptr32(_Words):  # noqa: N801 (the viper name)
    SIZE = 4


def ptr8(x):
    return x


def viper(f):
    """Run f as Python, with its ptr16/ptr32 arguments seen as word views."""
    code = f.__code__
    names = code.co_varnames[: code.co_argcount]
    annotations = f.__annotations__
    casts = [
        (i, annotations[name])
        for i, name in enumerate(names)
        if annotations.get(name) in (ptr16, ptr32)
    ]
    if not casts:
        return f

    @functools.wraps(f)
    def run(*args):
        args = list(args)
        for i, cast in casts:
            args[i] = cast(args[i])
        return f(*args)

    return run


for _ptr in (ptr8, ptr16, ptr32):
    setattr(builtins, _ptr.__name__, _ptr)
