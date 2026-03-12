"""Stub for the MicroPython framebuf module."""

GS4_HMSB = 2


class FrameBuffer:
    """Minimal FrameBuffer stub for testing display drivers on CPython."""

    def __init__(self, buffer, width, height, fmt):
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = fmt

    def fill(self, col):
        val = (col & 0x0F) | ((col & 0x0F) << 4)
        for i in range(len(self.buffer)):
            self.buffer[i] = val

    def pixel(self, x, y, col=None):
        pass

    def text(self, string, x, y, col=15):
        pass

    def line(self, x1, y1, x2, y2, col):
        pass

    def scroll(self, dx, dy):
        pass
