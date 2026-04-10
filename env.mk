export PATH := $(CURDIR)/node_modules/.bin:$(PATH)
PORT ?= /dev/ttyACM0

# Firmware build configuration
MICROPYTHON_REPO ?= https://github.com/steamicc/micropython-steami.git
MICROPYTHON_BRANCH ?= stm32-steami-rev1d-final
BOARD ?= STEAM32_WB55RG
BUILD_DIR ?= .build
MPY_DIR ?= $(BUILD_DIR)/micropython-steami
STM32_DIR = $(MPY_DIR)/ports/stm32
