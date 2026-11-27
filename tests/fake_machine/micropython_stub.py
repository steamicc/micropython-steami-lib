"""Stub for the micropython module, so const() and the code emitters work on CPython.

native and viper are identity decorators: the function runs as plain Python.
Viper annotates pointer arguments with ptr8, ptr16 and ptr32, names the board
compiler resolves by itself. Python 3.10 evaluates annotations when the def
runs, so importing this stub defines them as builtins (identity casts).
"""

import builtins


def const(x):
    return x


def native(f):
    return f


def viper(f):
    return f


def _ptr(x):
    return x


for _name in ("ptr8", "ptr16", "ptr32"):
    if not hasattr(builtins, _name):
        setattr(builtins, _name, _ptr)
