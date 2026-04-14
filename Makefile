.DEFAULT_GOAL := help

.ONESHELL: # Applies to every targets

include env.mk

# Venv path (override with VENV_DIR=/path for devcontainer)
VENV_DIR ?= .venv

# Use venv Python/tools when available, fallback to system
PYTHON := $(shell [ -x $(VENV_DIR)/bin/python ] && echo $(VENV_DIR)/bin/python || echo python3)

# --- Setup ---

# npm install is re-run only when package.json changes
node_modules/.package-lock.json: package.json package-lock.json
	npm install
	@touch $@

.PHONY: prepare
prepare: node_modules/.package-lock.json ## Install git hooks
	husky

.PHONY: setup
setup: install prepare ## Full dev environment setup

$(VENV_DIR)/bin/activate:
	python3 -m venv $(VENV_DIR)

.PHONY: install
install: $(VENV_DIR)/bin/activate node_modules/.package-lock.json ## Install dev tools (pip + npm)
	$(VENV_DIR)/bin/pip install -e ".[dev,test,flash]"

# --- Linting ---

.PHONY: lint
lint: ## Run ruff linter
	$(PYTHON) -m ruff check

.PHONY: lint-fix
lint-fix: ## Auto-fix lint issues
	$(PYTHON) -m ruff check --fix

# --- Testing ---

# Dynamic per-scenario targets (test-apds9960, test-hts221, etc.)
# Uses 'driver' field for driver scenarios, filename stem for board scenarios.
# Convention: for board scenarios, the YAML 'name' field must match the filename.
SCENARIOS := $(shell $(PYTHON) -c "import yaml,glob,os; [print(d.get('driver',os.path.basename(f).replace('.yaml',''))) for f in sorted(glob.glob('tests/scenarios/*.yaml')) for d in [yaml.safe_load(open(f))]]" 2>/dev/null)
$(foreach s,$(SCENARIOS),$(eval .PHONY: test-$(s))$(eval test-$(s): ; $(PYTHON) -m pytest tests/ -v -k "$(s)" --port $$(PORT) -s))

.PHONY: test-mock
test-mock: ## Run mock tests (no hardware needed)
	$(PYTHON) -m pytest tests/ -v -k mock

.PHONY: test
test: test-mock ## Run mock tests (use 'make test-all' for mock + hardware)
	@echo ""
	@echo "ℹ️  Only mock tests were run. Use 'make test-all' to include hardware tests."

.PHONY: test-hardware
test-hardware: ## Run all hardware tests (needs board on PORT)
	$(PYTHON) -m pytest tests/ -v --port $(PORT) -s -k hardware

.PHONY: test-board
test-board: ## Run board tests only (buttons, LEDs, buzzer, screen)
	$(PYTHON) -m pytest tests/ -v --port $(PORT) -s -k "board_ and hardware"

.PHONY: test-sensors
test-sensors: ## Run sensor driver hardware tests (I2C devices)
	$(PYTHON) -m pytest tests/ -v --port $(PORT) -s -k "hardware and not board_"

.PHONY: test-all
test-all: ## Run all tests (mock + hardware)
	$(PYTHON) -m pytest tests/ -v --port $(PORT) -s

.PHONY: test-examples
test-examples: ## Validate all example files (syntax + imports)
	$(PYTHON) -m pytest tests/test_examples.py -v

# --- CI ---

.PHONY: ci
ci: lint test test-examples ## Run all CI checks (lint + tests + examples)

# --- Build / Package ---

.PHONY: build
build: lint test ## Build (lint + test)

# --- MicroPython firmware ---

$(MPY_DIR):
	@echo "Cloning micropython-steami into $(CURDIR)/$(MPY_DIR)..."
	@mkdir -p $(dir $(CURDIR)/$(MPY_DIR))
	git clone --branch $(MICROPYTHON_BRANCH) $(MICROPYTHON_REPO) $(CURDIR)/$(MPY_DIR)
	$(MAKE) -C $(STM32_DIR) BOARD=$(BOARD) submodules

.PHONY: micropython-firmware
micropython-firmware: $(MPY_DIR) ## Build MicroPython firmware with current drivers
	@set -e
	@if [ ! -f "$(MPY_DIR)/lib/micropython-lib/README.md" ]; then \
		echo "Initializing submodules for $(BOARD)..."; \
		$(MAKE) -C $(STM32_DIR) BOARD=$(BOARD) submodules; \
	fi
	@echo "Linking local drivers..."
	rm -rf $(CURDIR)/$(MPY_DIR)/lib/micropython-steami-lib
	ln -s $(CURDIR) $(CURDIR)/$(MPY_DIR)/lib/micropython-steami-lib
	@echo "Building firmware for $(BOARD)..."
	rm -f $(STM32_DIR)/build-$(BOARD)/frozen_content.c
	$(MAKE) -C $(STM32_DIR) BOARD=$(BOARD)
	@echo "Firmware ready: $(STM32_DIR)/build-$(BOARD)/firmware.hex"

.PHONY: micropython-update
micropython-update: $(MPY_DIR) ## Update the MicroPython clone and board-specific submodules
	@set -e
	@echo "Updating micropython-steami..."
	rm -rf $(CURDIR)/$(MPY_DIR)/lib/micropython-steami-lib
	git -C $(CURDIR)/$(MPY_DIR) fetch origin
	git -C $(CURDIR)/$(MPY_DIR) checkout $(MICROPYTHON_BRANCH)
	git -C $(CURDIR)/$(MPY_DIR) checkout -- lib/micropython-steami-lib
	git -C $(CURDIR)/$(MPY_DIR) pull --ff-only
	@echo "Updating required submodules for $(BOARD)..."
	$(MAKE) -C $(STM32_DIR) BOARD=$(BOARD) submodules

.PHONY: micropython-deploy
micropython-deploy: micropython-deploy-pyocd ## Flash MicroPython firmware (default: pyocd)

.PHONY: micropython-deploy-pyocd
micropython-deploy-pyocd: $(MPY_DIR) ## Flash MicroPython firmware via pyOCD (CMSIS-DAP)
	$(PYTHON) -m pyocd flash $(STM32_DIR)/build-$(BOARD)/firmware.elf --format elf

.PHONY: micropython-deploy-openocd
micropython-deploy-openocd: $(MPY_DIR) ## Flash MicroPython firmware via OpenOCD
	$(MAKE) -C $(STM32_DIR) BOARD=$(BOARD) deploy-openocd

.PHONY: micropython-deploy-usb
micropython-deploy-usb: $(MPY_DIR) ## Flash MicroPython firmware via DAPLink USB mass-storage
	@$(PYTHON) scripts/deploy_usb.py \
		--build-target micropython-firmware \
		$(STM32_DIR)/build-$(BOARD)/firmware.bin

# --- Deprecated targets (ambiguous since DAPLink build is also planned) ---
# Replaced by explicit micropython-* / daplink-* targets to avoid confusion
# about which firmware is being built or flashed.

define DEPRECATED_FIRMWARE
@echo "Error: 'make $(1)' is ambiguous. Use one of:"; \
echo "  make micropython-$(2)   (MicroPython firmware)"; \
echo "  make daplink-$(2)       (DAPLink firmware)"; \
exit 1
endef

.PHONY: firmware firmware-update firmware-clean deploy deploy-pyocd deploy-openocd deploy-usb
firmware:
	$(call DEPRECATED_FIRMWARE,firmware,firmware)
firmware-update:
	$(call DEPRECATED_FIRMWARE,firmware-update,update)
firmware-clean:
	$(call DEPRECATED_FIRMWARE,firmware-clean,clean)
deploy:
	$(call DEPRECATED_FIRMWARE,deploy,deploy)
deploy-pyocd:
	$(call DEPRECATED_FIRMWARE,deploy-pyocd,deploy-pyocd)
deploy-openocd:
	$(call DEPRECATED_FIRMWARE,deploy-openocd,deploy-openocd)
deploy-usb:
	$(call DEPRECATED_FIRMWARE,deploy-usb,deploy-usb)

.PHONY: run
run: ## Run a script on the board with live output (SCRIPT=path/to/file.py)
	@if [ -z "$(SCRIPT)" ]; then \
		echo "Error: SCRIPT is required. Usage: make run SCRIPT=lib/.../example.py"; exit 1; \
	fi
	$(PYTHON) -m mpremote connect $(PORT) run $(SCRIPT)

.PHONY: deploy-script
deploy-script: ## Deploy a script as main.py for autonomous execution (SCRIPT=path/to/file.py)
	@if [ -z "$(SCRIPT)" ]; then \
		echo "Error: SCRIPT is required. Usage: make deploy-script SCRIPT=lib/.../example.py"; exit 1; \
	fi
	$(PYTHON) -m mpremote connect $(PORT) cp $(SCRIPT) :main.py
	$(PYTHON) -m mpremote connect $(PORT) reset
	@echo "Script deployed as main.py and board reset."

.PHONY: run-main
run-main: ## Re-execute main.py on the board and capture output
	$(PYTHON) -m mpremote connect $(PORT) exec "exec(open('/flash/main.py').read())"

.PHONY: micropython-clean
micropython-clean: ## Clean MicroPython firmware build artifacts
	@if [ -d "$(STM32_DIR)" ]; then \
		$(MAKE) -C $(STM32_DIR) BOARD=$(BOARD) clean; \
	fi

# --- DAPLink firmware ---
# These targets build and flash the DAPLink firmware that runs on the
# STM32F103 interface chip. DAPLink has two parts:
#
#   * Bootloader (first stage, `stm32f103xb_bl`) at 0x08000000
#       → rarely updated, requires an external SWD probe.
#   * Interface firmware (second stage, `stm32f103xb_steami32_if`) at 0x08002000
#       → updated routinely, typically via the MAINTENANCE USB volume,
#         or via an external SWD probe for recovery / bricked boards.
#
# SWD targets (`daplink-deploy-pyocd`, `daplink-deploy-openocd`,
# `daplink-deploy-bootloader*`) need an EXTERNAL probe (ST-Link, J-Link, or
# another CMSIS-DAP board) connected to the SWD header of the target board.
# A board cannot reflash its own DAPLink chip via its own SWD pins.

define DAPLINK_SWD_WARNING
@echo "================================================================"
@echo "Warning: this target flashes the DAPLink chip via SWD."
@echo "Requires an EXTERNAL probe (ST-Link / J-Link / CMSIS-DAP)"
@echo "connected to the target board's SWD header. A board cannot"
@echo "reflash its own on-board DAPLink via its own SWD pins."
@echo "================================================================"
endef

define DAPLINK_OPENOCD_FLASH
openocd -f $(DAPLINK_OPENOCD_INTERFACE) \
	-f $(DAPLINK_OPENOCD_TARGET) \
	-c "transport select $(DAPLINK_OPENOCD_TRANSPORT)" \
	-c "reset_config none separate" \
	-c "init" \
	-c "reset halt" \
	-c "stm32f1x unlock 0" \
	-c "reset halt" \
	-c "program $(1) verify $(2)" \
	-c "reset; exit"
endef

$(DAPLINK_DIR):
	@echo "Cloning DAPLink into $(CURDIR)/$(DAPLINK_DIR)..."
	@mkdir -p $(dir $(CURDIR)/$(DAPLINK_DIR))
	git clone --branch $(DAPLINK_BRANCH) $(DAPLINK_REPO) $(CURDIR)/$(DAPLINK_DIR)

$(DAPLINK_GCC_DIR)/bin/arm-none-eabi-gcc:
	@set -e
	@if [ -z "$(DAPLINK_GCC_ARCHIVE)" ]; then \
		echo "Error: no prebuilt gcc-arm-none-eabi $(DAPLINK_GCC_VERSION) for $(DAPLINK_GCC_HOST_OS)/$(DAPLINK_GCC_HOST_ARCH)."; \
		echo "Supported by this target: Linux x86_64, Linux aarch64, macOS Intel."; \
		echo "Other platforms: install the toolchain manually and override DAPLINK_GCC_DIR,"; \
		echo "or build inside the dev container."; \
		exit 1; \
	fi
	@echo "Downloading gcc-arm-none-eabi $(DAPLINK_GCC_VERSION) for $(DAPLINK_GCC_HOST_OS)/$(DAPLINK_GCC_HOST_ARCH)..."
	@mkdir -p $(BUILD_DIR)
	curl -fL -o $(BUILD_DIR)/gcc-arm-none-eabi.tar.bz2 "$(DAPLINK_GCC_URL)"
	tar -xjf $(BUILD_DIR)/gcc-arm-none-eabi.tar.bz2 -C $(BUILD_DIR)
	rm -f $(BUILD_DIR)/gcc-arm-none-eabi.tar.bz2

# Sentinel: re-runs pip install whenever DAPLink's requirements.txt changes
# (e.g. after `make daplink-update`). The order-only prerequisite on
# $(DAPLINK_DIR) guarantees the clone happens first on a fresh checkout, so
# requirements.txt exists by the time make checks it.
$(DAPLINK_DIR)/venv/.installed: $(DAPLINK_DIR)/requirements.txt | $(DAPLINK_DIR)
	@echo "Setting up DAPLink Python virtualenv..."
	@if [ ! -x "$(DAPLINK_DIR)/venv/bin/python" ]; then \
		$(PYTHON) -m venv $(DAPLINK_DIR)/venv; \
	fi
	$(DAPLINK_DIR)/venv/bin/pip install -r $(DAPLINK_DIR)/requirements.txt
	@touch $@

.PHONY: daplink-firmware
daplink-firmware: $(DAPLINK_DIR) $(DAPLINK_GCC_DIR)/bin/arm-none-eabi-gcc $(DAPLINK_DIR)/venv/.installed ## Build DAPLink interface firmware for the STeaMi STM32F103
	@echo "Building DAPLink target $(DAPLINK_TARGET) with gcc-arm-none-eabi $(DAPLINK_GCC_VERSION)..."
	cd $(CURDIR)/$(DAPLINK_DIR) && \
		PATH="$(CURDIR)/$(DAPLINK_GCC_DIR)/bin:$(CURDIR)/$(DAPLINK_DIR)/venv/bin:$$PATH" \
		./venv/bin/python tools/progen_compile.py -t make_gcc_arm $(DAPLINK_TARGET)
	@echo "DAPLink firmware ready: $(DAPLINK_BUILD_DIR)/$(DAPLINK_TARGET)_crc.bin"

.PHONY: daplink-bootloader
daplink-bootloader: $(DAPLINK_DIR) $(DAPLINK_GCC_DIR)/bin/arm-none-eabi-gcc $(DAPLINK_DIR)/venv/.installed ## Build DAPLink bootloader for the STeaMi STM32F103
	@echo "Building DAPLink target $(DAPLINK_BL_TARGET) with gcc-arm-none-eabi $(DAPLINK_GCC_VERSION)..."
	cd $(CURDIR)/$(DAPLINK_DIR) && \
		PATH="$(CURDIR)/$(DAPLINK_GCC_DIR)/bin:$(CURDIR)/$(DAPLINK_DIR)/venv/bin:$$PATH" \
		./venv/bin/python tools/progen_compile.py -t make_gcc_arm $(DAPLINK_BL_TARGET)
	@echo "DAPLink bootloader ready: $(DAPLINK_BL_BUILD_DIR)/$(DAPLINK_BL_TARGET)_crc.bin"

.PHONY: daplink-update
daplink-update: $(DAPLINK_DIR) ## Update the DAPLink clone
	@set -e
	@echo "Updating DAPLink..."
	git -C $(CURDIR)/$(DAPLINK_DIR) fetch origin
	git -C $(CURDIR)/$(DAPLINK_DIR) checkout $(DAPLINK_BRANCH)
	git -C $(CURDIR)/$(DAPLINK_DIR) pull --ff-only

.PHONY: daplink-deploy
daplink-deploy: daplink-deploy-usb ## Flash DAPLink interface firmware (default: usb mass-storage)

.PHONY: daplink-deploy-usb
daplink-deploy-usb: $(DAPLINK_DIR) ## Flash DAPLink interface firmware via MAINTENANCE USB mass-storage
	@echo "Note: the board must be in MAINTENANCE mode."
	@echo "Power on the board with the RESET button held until the MAINTENANCE volume appears."
	@echo ""
	@$(PYTHON) scripts/deploy_usb.py --label MAINTENANCE \
		--build-target daplink-firmware \
		$(DAPLINK_BUILD_DIR)/$(DAPLINK_TARGET)_crc.bin

.PHONY: daplink-deploy-pyocd
daplink-deploy-pyocd: daplink-firmware ## Flash DAPLink interface firmware via external SWD probe (pyocd)
	$(DAPLINK_SWD_WARNING)
	$(PYTHON) -m pyocd flash -t $(DAPLINK_PYOCD_TARGET) \
		--base-address $(DAPLINK_FLASH_ADDR) \
		$(DAPLINK_BUILD_DIR)/$(DAPLINK_TARGET)_crc.bin

.PHONY: daplink-deploy-openocd
daplink-deploy-openocd: daplink-firmware ## Flash DAPLink interface firmware via external SWD probe (openocd)
	$(DAPLINK_SWD_WARNING)
	$(call DAPLINK_OPENOCD_FLASH,$(DAPLINK_BUILD_DIR)/$(DAPLINK_TARGET)_crc.bin,$(DAPLINK_FLASH_ADDR))

.PHONY: daplink-deploy-bootloader
daplink-deploy-bootloader: daplink-deploy-bootloader-pyocd ## Flash DAPLink bootloader via external SWD probe (default: pyocd)

.PHONY: daplink-deploy-bootloader-pyocd
daplink-deploy-bootloader-pyocd: daplink-bootloader ## Flash DAPLink bootloader via external SWD probe (pyocd)
	$(DAPLINK_SWD_WARNING)
	$(PYTHON) -m pyocd flash -t $(DAPLINK_PYOCD_TARGET) \
		--base-address $(DAPLINK_BL_FLASH_ADDR) \
		$(DAPLINK_BL_BUILD_DIR)/$(DAPLINK_BL_TARGET)_crc.bin

.PHONY: daplink-deploy-bootloader-openocd
daplink-deploy-bootloader-openocd: daplink-bootloader ## Flash DAPLink bootloader via external SWD probe (openocd)
	$(DAPLINK_SWD_WARNING)
	$(call DAPLINK_OPENOCD_FLASH,$(DAPLINK_BL_BUILD_DIR)/$(DAPLINK_BL_TARGET)_crc.bin,$(DAPLINK_BL_FLASH_ADDR))

.PHONY: daplink-clean
daplink-clean: ## Clean DAPLink firmware build artifacts
	@if [ -d "$(DAPLINK_DIR)" ]; then \
		rm -rf $(DAPLINK_DIR)/projectfiles; \
	fi

# --- Hardware ---

.PHONY: repl
repl: ## Open MicroPython REPL on the board
	$(PYTHON) -m mpremote connect $(PORT)

.PHONY: mount
mount: ## Mount lib/ on the board for live testing
	$(PYTHON) -m mpremote connect $(PORT) mount lib/

.PHONY: list-frozen
list-frozen: ## List frozen modules on the connected board
	@$(PYTHON) -m mpremote connect $(PORT) exec "help('modules')"
	@echo ""
	@echo "--- Frozen driver modules ---"
	@$(PYTHON) -m mpremote connect $(PORT) run scripts/list_frozen_drivers.py

# --- Release ---

PART ?= patch

.PHONY: bump
bump: ## Create a version tag (PART=patch|minor|major, default: patch)
	@echo "Note: releases are normally handled by semantic-release in CI."
	@echo "Use 'make bump' only to force a specific version.\n"
	@if [ "$$(git symbolic-ref --short HEAD)" != "main" ]; then \
		echo "Error: bump must be run on the main branch."; exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: working tree is not clean. Commit or stash changes first."; exit 1; \
	fi
	@set -e; \
	LAST=$$(git tag --sort=-v:refname | head -1); \
	if [ -z "$$LAST" ]; then \
		NEXT="v1.0.0"; \
	else \
		if ! echo "$$LAST" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$$'; then \
			echo "Error: latest tag '$$LAST' is not in supported format v<major>.<minor>.<patch>."; exit 1; \
		fi; \
		MAJOR=$$(echo "$$LAST" | sed 's/^v//' | cut -d. -f1); \
		MINOR=$$(echo "$$LAST" | sed 's/^v//' | cut -d. -f2); \
		PATCH=$$(echo "$$LAST" | sed 's/^v//' | cut -d. -f3); \
		case "$(PART)" in \
			major) MAJOR=$$((MAJOR + 1)); MINOR=0; PATCH=0 ;; \
			minor) MINOR=$$((MINOR + 1)); PATCH=0 ;; \
			patch) PATCH=$$((PATCH + 1)) ;; \
			*) echo "Error: PART must be patch, minor or major."; exit 1 ;; \
		esac; \
		NEXT="v$$MAJOR.$$MINOR.$$PATCH"; \
	fi; \
	echo "$$LAST → $$NEXT"; \
	VERSION=$${NEXT#v}; \
	$(PYTHON) -c "import re, pathlib; p=pathlib.Path('pyproject.toml'); p.write_text(re.sub(r'^version = \".*\"', 'version = \"$$VERSION\"', p.read_text(), count=1, flags=re.MULTILINE))"; \
	git add pyproject.toml; \
	git commit -m "chore: Bump version to $$NEXT."; \
	git tag -a "$$NEXT" -m "Release $$NEXT"; \
	git push origin main "$$NEXT"; \
	echo "Tag $$NEXT pushed to origin."

# --- Utilities ---

.PHONY: clean
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true

.PHONY: deepclean
deepclean: clean ## Remove everything including node_modules, venv and firmware
	rm -rf node_modules $(VENV_DIR)
	@if [ -d "$(BUILD_DIR)" ]; then rm -rf "$(BUILD_DIR)"; fi

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# A useful debug Make Target - found from
# http://lists.gnu.org/archive/html/help-make/2005-08/msg00137.html
.PHONY: printvars
printvars:
	@$(foreach V,$(sort $(.VARIABLES)), \
	$(if $(filter-out environment% default automatic, \
	$(origin $V)),$(warning $V=$($V) ($(value $V)))))

# Affiche toutes les cibles disponibles dans le Makefile
.PHONY: list
list:
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'
