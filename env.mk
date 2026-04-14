export PATH := $(CURDIR)/node_modules/.bin:$(PATH)
PORT ?= /dev/ttyACM0

BUILD_DIR ?= .build

# MicroPython firmware build configuration
MICROPYTHON_REPO ?= https://github.com/steamicc/micropython-steami.git
MICROPYTHON_BRANCH ?= stm32-steami-rev1d-final
BOARD ?= STEAM32_WB55RG
MPY_DIR ?= $(BUILD_DIR)/micropython-steami
STM32_DIR ?= $(MPY_DIR)/ports/stm32

# DAPLink firmware build configuration
DAPLINK_REPO ?= https://github.com/steamicc/DAPLink.git
DAPLINK_BRANCH ?= release_letssteam
DAPLINK_DIR ?= $(BUILD_DIR)/DAPLink
DAPLINK_TARGET ?= stm32f103xb_steami32_if
DAPLINK_BUILD_DIR ?= $(DAPLINK_DIR)/projectfiles/make_gcc_arm/$(DAPLINK_TARGET)/build
DAPLINK_BL_TARGET ?= stm32f103xb_bl
DAPLINK_BL_BUILD_DIR ?= $(DAPLINK_DIR)/projectfiles/make_gcc_arm/$(DAPLINK_BL_TARGET)/build

# SWD flash configuration (external probe). Used by the `daplink-deploy-*`
# SWD targets. The STM32F103CB on the DAPLink chip is flash-compatible with
# pyOCD's built-in stm32f103rc target for the lower 128 KB.
DAPLINK_FLASH_ADDR ?= 0x08002000
DAPLINK_BL_FLASH_ADDR ?= 0x08000000
DAPLINK_PYOCD_TARGET ?= stm32f103rc
DAPLINK_OPENOCD_INTERFACE ?= interface/stlink.cfg
DAPLINK_OPENOCD_TARGET ?= target/stm32f1x.cfg
DAPLINK_OPENOCD_TRANSPORT ?= hla_swd

# DAPLink requires gcc-arm-none-eabi 10.3-2021.10. System toolchains >= 11.3
# produce code that overflows m_text (see DAPLink docs/DEVELOPERS-GUIDE.md and
# ARMmbed/DAPLink#1043). The toolchain is downloaded once into BUILD_DIR.
#
# ARM publishes 10.3-2021.10 binaries for: x86_64 Linux, aarch64 Linux, and
# Intel macOS. Apple Silicon and Windows are NOT supported by this target —
# users on those platforms must install the toolchain manually and override
# DAPLINK_GCC_DIR / DAPLINK_GCC_URL, or build inside the dev container.
DAPLINK_GCC_VERSION ?= 10.3-2021.10
DAPLINK_GCC_DIR ?= $(BUILD_DIR)/gcc-arm-none-eabi-$(DAPLINK_GCC_VERSION)

DAPLINK_GCC_HOST_OS := $(shell uname -s)
DAPLINK_GCC_HOST_ARCH := $(shell uname -m)
ifeq ($(DAPLINK_GCC_HOST_OS),Linux)
    ifeq ($(DAPLINK_GCC_HOST_ARCH),x86_64)
        DAPLINK_GCC_ARCHIVE ?= gcc-arm-none-eabi-$(DAPLINK_GCC_VERSION)-x86_64-linux.tar.bz2
    else ifeq ($(DAPLINK_GCC_HOST_ARCH),aarch64)
        DAPLINK_GCC_ARCHIVE ?= gcc-arm-none-eabi-$(DAPLINK_GCC_VERSION)-aarch64-linux.tar.bz2
    endif
else ifeq ($(DAPLINK_GCC_HOST_OS),Darwin)
    ifeq ($(DAPLINK_GCC_HOST_ARCH),x86_64)
        DAPLINK_GCC_ARCHIVE ?= gcc-arm-none-eabi-$(DAPLINK_GCC_VERSION)-mac.tar.bz2
    endif
endif
DAPLINK_GCC_URL ?= https://developer.arm.com/-/media/Files/downloads/gnu-rm/$(DAPLINK_GCC_VERSION)/$(DAPLINK_GCC_ARCHIVE)
