SHELL=/usr/bin/env bash
# Minimal Makefile for OpenHands V1

# ANSI color codes
GREEN=$(shell tput -Txterm setaf 2)
YELLOW=$(shell tput -Txterm setaf 3)
BLUE=$(shell tput -Txterm setaf 6)
RESET=$(shell tput -Txterm sgr0)

# Install all dependencies
install:
	@echo "$(YELLOW)Installing dependencies with uv...$(RESET)"
	@uv sync --dev
	@echo "$(GREEN)Dependencies installed successfully.$(RESET)"

# Setup pre-commit hooks
setup-hooks:
	@echo "$(YELLOW)Setting up pre-commit hooks...$(RESET)"
	@uv run pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed successfully.$(RESET)"

# Format code using uv format
format:
	@echo "$(YELLOW)Formatting code with uv format...$(RESET)"
	@uv run --with ruff ruff format .
	@echo "$(GREEN)Code formatted successfully.$(RESET)"

# Lint code
lint:
	@echo "$(YELLOW)Linting code with ruff...$(RESET)"
	@uv run ruff check .
	@echo "$(GREEN)Linting completed.$(RESET)"

# Run linting and formatting
check: lint format

# Full setup: install deps and setup hooks
setup: install setup-hooks
	@echo "$(GREEN)Setup completed successfully.$(RESET)"

# Clean up cache and build artifacts
clean:
	@echo "$(YELLOW)Cleaning up...$(RESET)"
	@rm -rf .ruff_cache __pycache__ .pytest_cache
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@echo "$(GREEN)Cleanup completed.$(RESET)"

# Help
help:
	@echo "$(BLUE)OpenHands V1 Makefile$(RESET)"
	@echo "Available targets:"
	@echo "  $(GREEN)install$(RESET)      - Install Python dependencies with uv"
	@echo "  $(GREEN)setup-hooks$(RESET)  - Setup pre-commit hooks"
	@echo "  $(GREEN)format$(RESET)       - Format code with uv format"
	@echo "  $(GREEN)lint$(RESET)         - Lint code with ruff"
	@echo "  $(GREEN)check$(RESET)        - Run lint and format"
	@echo "  $(GREEN)setup$(RESET)        - Full setup (install + hooks)"
	@echo "  $(GREEN)clean$(RESET)        - Clean up cache files"
	@echo "  $(GREEN)help$(RESET)         - Show this help message"

.PHONY: install setup-hooks format lint check setup clean help