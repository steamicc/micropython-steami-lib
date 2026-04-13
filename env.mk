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
