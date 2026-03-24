.DEFAULT_GOAL := help

.ONESHELL: # Applies to every targets

include env.mk

# --- Setup ---

# npm install is re-run only when package.json changes
node_modules/.package-lock.json: package.json
	npm install
	@touch $@

.PHONY: prepare
prepare: node_modules/.package-lock.json ## Install git hooks
	husky

.PHONY: setup
setup: install prepare ## Full dev environment setup

.PHONY: install
install: node_modules/.package-lock.json ## Install dev tools (pip + npm)
	pip install -e ".[dev,test]"

# --- Linting ---

.PHONY: lint
lint: ## Run ruff linter
	ruff check

.PHONY: lint-fix
lint-fix: ## Auto-fix lint issues
	ruff check --fix

# --- Testing ---

# Dynamic per-scenario targets (test-apds9960, test-hts221, etc.)
SCENARIOS := $(basename $(notdir $(wildcard tests/scenarios/*.yaml)))
$(foreach s,$(SCENARIOS),$(eval .PHONY: test-$(s))$(eval test-$(s): ; python3 -m pytest tests/ -v -k "$(s)" --port $$(PORT) -s))

.PHONY: test-mock
test-mock: ## Run mock tests (no hardware needed)
	python3 -m pytest tests/ -v -k mock

.PHONY: test
test: test-mock ## Run mock tests (use 'make test-all' for mock + hardware)
	@echo ""
	@echo "ℹ️  Only mock tests were run. Use 'make test-all' to include hardware tests."

.PHONY: test-hardware
test-hardware: ## Run all hardware tests (needs board on PORT)
	python3 -m pytest tests/ -v --port $(PORT) -s -k hardware

.PHONY: test-board
test-board: ## Run board tests only (buttons, LEDs, buzzer, screen)
	python3 -m pytest tests/ -v --port $(PORT) -s -k "board_ and hardware"

.PHONY: test-sensors
test-sensors: ## Run sensor driver hardware tests (I2C devices)
	python3 -m pytest tests/ -v --port $(PORT) -s -k "hardware and not board_"

.PHONY: test-all
test-all: ## Run all tests (mock + hardware)
	python3 -m pytest tests/ -v --port $(PORT) -s

.PHONY: test-examples
test-examples: ## Validate all example files (syntax + imports)
	python3 -m pytest tests/test_examples.py -v

# --- CI ---

.PHONY: ci
ci: lint test test-examples ## Run all CI checks (lint + tests + examples)

# --- Build / Package ---

.PHONY: build
build: lint test ## Build (lint + test)

# --- Hardware ---

.PHONY: repl
repl: ## Open MicroPython REPL on the board
	mpremote connect $(PORT)

.PHONY: mount
mount: ## Mount lib/ on the board for live testing
	mpremote connect $(PORT) mount lib/

# --- Utilities ---

.PHONY: clean
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

.PHONY: deepclean
deepclean: clean ## Remove everything including node_modules
	rm -rf node_modules

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