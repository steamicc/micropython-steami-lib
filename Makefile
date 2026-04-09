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
	$(VENV_DIR)/bin/pip install -e ".[dev,test]"

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

# --- Firmware ---

$(MPY_DIR):
	@echo "Cloning micropython-steami into $(CURDIR)/$(MPY_DIR)..."
	@mkdir -p $(dir $(CURDIR)/$(MPY_DIR))
	git clone --branch $(MICROPYTHON_BRANCH) $(MICROPYTHON_REPO) $(CURDIR)/$(MPY_DIR)
	cd $(CURDIR)/$(MPY_DIR)/ports/stm32 && $(MAKE) BOARD=$(BOARD) submodules

.PHONY: firmware
firmware: $(MPY_DIR) ## Build MicroPython firmware with current drivers
	@if [ ! -f "$(MPY_DIR)/lib/micropython-lib/README.md" ]; then \
		echo "Initializing submodules for $(BOARD)..."; \
		cd $(CURDIR)/$(MPY_DIR)/ports/stm32 && $(MAKE) BOARD=$(BOARD) submodules; \
	fi
	@echo "Linking local drivers..."
	rm -rf $(CURDIR)/$(MPY_DIR)/lib/micropython-steami-lib
	ln -s $(CURDIR) $(CURDIR)/$(MPY_DIR)/lib/micropython-steami-lib
	@echo "Building firmware for $(BOARD)..."
	cd $(CURDIR)/$(MPY_DIR)/ports/stm32 && $(MAKE) BOARD=$(BOARD)
	@echo "Firmware ready: $(CURDIR)/$(MPY_DIR)/ports/stm32/build-$(BOARD)/firmware.hex"

.PHONY: firmware-update
firmware-update: $(MPY_DIR) ## Update the MicroPython clone and board-specific submodules
	@echo "Updating micropython-steami..."
	rm -rf $(CURDIR)/$(MPY_DIR)/lib/micropython-steami-lib
	cd $(CURDIR)/$(MPY_DIR) && git fetch origin && git checkout $(MICROPYTHON_BRANCH) && git checkout -- lib/micropython-steami-lib && git pull --ff-only
	@echo "Updating required submodules for $(BOARD)..."
	cd $(CURDIR)/$(MPY_DIR)/ports/stm32 && $(MAKE) BOARD=$(BOARD) submodules

.PHONY: deploy
deploy: $(MPY_DIR) ## Flash firmware to the board via OpenOCD
	cd $(CURDIR)/$(MPY_DIR)/ports/stm32 && $(MAKE) BOARD=$(BOARD) deploy-openocd

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

.PHONY: firmware-clean
firmware-clean: ## Clean firmware build artifacts
	@if [ -d "$(MPY_DIR)/ports/stm32" ]; then \
		cd $(MPY_DIR)/ports/stm32 && $(MAKE) BOARD=$(BOARD) clean; \
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
