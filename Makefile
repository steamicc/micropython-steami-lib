.DEFAULT_GOAL := help

PORT ?= /dev/ttyACM0

# --- Setup ---

.PHONY: prepare
prepare: ## Install git hooks
	husky

.PHONY: setup
setup: install prepare ## Full dev environment setup

.PHONY: install
install: ## Install dev tools (pip + npm)
	pip install ruff pytest
	npm install

# --- Linting ---

.PHONY: lint
lint: ## Run ruff linter
	ruff check

.PHONY: lint-fix
lint-fix: ## Auto-fix lint issues
	ruff check --fix

# --- Testing ---

.PHONY: test
test: ## Run all mock tests (no hardware needed)
	python3 -m pytest tests/ -v -k mock

.PHONY: test-hw
test-hw: ## Run hardware tests (needs board on PORT)
	python3 -m pytest tests/ -v --port $(PORT) -s

.PHONY: test-all
test-all: ## Run all tests (mock + hardware)
	python3 -m pytest tests/ -v --port $(PORT) -s

.PHONY: test-driver
test-driver: ## Run tests for one driver (usage: make test-driver DRIVER=hts221)
	python3 -m pytest tests/ -v -k "$(DRIVER)" --port $(PORT) -s

.PHONY: test-examples
test-examples: ## Validate all example files (syntax + imports)
	python3 -m pytest tests/test_examples.py -v

# --- CI ---

.PHONY: ci
ci: lint test test-examples ## Run all CI checks (lint + tests + examples)

# --- Build / Package ---

.PHONY: build
build: lint test ## Build (lint + test)

.PHONY: package
package: ## Package drivers for distribution
	@echo "Packaging not yet implemented (see issue backlog)"

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

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
