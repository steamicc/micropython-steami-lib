FROM mcr.microsoft.com/devcontainers/python:3.10

# System packages for MicroPython and DAPLink firmware builds, board communication
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc-arm-none-eabi \
    libnewlib-arm-none-eabi \
    openocd \
    udev \
    ccache \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# udev rules for STeaMi board (DAPLink / STM32)
RUN mkdir -p /etc/udev/rules.d \
    && echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0d28", MODE="0666"' \
    > /etc/udev/rules.d/99-steami.rules
