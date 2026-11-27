"""Tests of the micropython stub's viper emulation on CPython.

On the board, a viper argument annotated ptr16 or ptr32 is the address of
the buffer: indexing it reads or writes native (little-endian on the
STM32) 16- or 32-bit words, with no bounds check. The stub views such
arguments as word arrays over the same bytes, so a viper function run on
the host gives the bytes the board would, and an index outside the buffer
fails instead of corrupting memory.
"""

import pytest

from tests.fake_machine import micropython_stub as micropython


@micropython.viper
def _copy_words(src: ptr16, dst: ptr16, n: int):  # noqa: F821
    for i in range(n):
        dst[i] = src[i]


@micropython.viper
def _poke16(buf: ptr16, i: int, v: int):  # noqa: F821
    buf[i] = v


@micropython.viper
def _peek16(buf: ptr16, i: int) -> int:  # noqa: F821
    return buf[i]


@micropython.viper
def _poke32(buf: ptr32, i: int, v: int):  # noqa: F821
    buf[i] = v


@micropython.viper
def _first_byte(buf: ptr8) -> int:  # noqa: F821
    return buf[0]


def test_ptr16_reads_little_endian_words():
    assert _peek16(bytearray(b"\x34\x12\x78\x56"), 1) == 0x5678


def test_ptr16_writes_little_endian_words_truncated_to_16_bits():
    buf = bytearray(4)
    _poke16(buf, 1, 0x1ABCD)
    assert buf == b"\x00\x00\xcd\xab"


def test_ptr32_writes_little_endian_words():
    buf = bytearray(8)
    _poke32(buf, 1, 0x12345678)
    assert buf == b"\x00\x00\x00\x00\x78\x56\x34\x12"


def test_copying_words_keeps_the_bytes():
    src = bytearray(range(1, 9))
    dst = bytearray(8)
    _copy_words(src, dst, 4)
    assert dst == src


def test_ptr16_writes_through_the_given_buffer():
    # A bytearray subclass sees every byte access (the driver tests guard
    # their buffers this way).
    seen = []

    class Logged(bytearray):
        def __setitem__(self, i, v):
            seen.append(i)
            super().__setitem__(i, v)

    buf = Logged(4)
    _poke16(buf, 1, 0xFFFF)
    assert sorted(seen) == [2, 3]
    assert buf == b"\x00\x00\xff\xff"


@pytest.mark.parametrize("i", [-1, 2])
def test_ptr16_index_outside_the_buffer_fails(i):
    with pytest.raises(IndexError):
        _poke16(bytearray(4), i, 0)
    with pytest.raises(IndexError):
        _peek16(bytearray(4), i)


def test_ptr8_argument_is_the_buffer_itself():
    assert _first_byte(b"\x2a") == 42


def test_viper_without_pointer_arguments_is_the_function_itself():
    def f(a: int) -> int:
        return a

    assert micropython.viper(f) is f
    assert micropython.native(f) is f
