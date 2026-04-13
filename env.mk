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

# DAPLink requires gcc-arm-none-eabi 10.3-2021.10. System toolchains >= 11.3
# produce code that overflows m_text (see DAPLink docs/DEVELOPERS-GUIDE.md and
# ARMmbed/DAPLink#1043). The toolchain is downloaded once into BUILD_DIR.
DAPLINK_GCC_VERSION ?= 10.3-2021.10
DAPLINK_GCC_DIR ?= $(BUILD_DIR)/gcc-arm-none-eabi-$(DAPLINK_GCC_VERSION)
DAPLINK_GCC_URL ?= https://developer.arm.com/-/media/Files/downloads/gnu-rm/$(DAPLINK_GCC_VERSION)/gcc-arm-none-eabi-$(DAPLINK_GCC_VERSION)-x86_64-linux.tar.bz2
