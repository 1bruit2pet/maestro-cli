# Maestro CLI Makefile
# Usage: make <target>

.PHONY: help install develop test lint format clean

# Python executable
PYTHON ?= python3
PIP ?= pip3

# Project name
NAME = maestro-cli

# Default target
help:
	@echo "Maestro CLI - AI-Assisted Music Production"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install the package in development mode"
	@echo "  develop      - Install with all development dependencies"
	@echo "  test        - Run all tests"
	@echo "  lint        - Run linter (ruff)"
	@echo "  format      - Format code (ruff)"
	@echo "  type        - Run type checker (mypy)"
	@echo "  clean       - Remove build artifacts"
	@echo "  all         - Run lint, format, type, and test"
	@echo ""
	@echo "Project commands:"
	@echo "  maestro      - Run the CLI"
	@echo "  maestro --help - Show CLI help"

# Install the package
install:
	$(PIP) install -e .

# Install with development dependencies
develop:
	$(PIP) install -e ".[dev]"

# Run tests
test:
	$(PYTHON) -m pytest -v

# Run linter
lint:
	$(PYTHON) -m ruff check .

# Format code
format:
	$(PYTHON) -m ruff format .

# Type checking
type:
	$(PYTHON) -m mypy .

# Run all checks
all: lint format type test

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned build artifacts"

# Create a demo project
demo:
	$(PYTHON) -m $(NAME) init demo_song --title "Demo Song" --style gospel --bpm 100 --key C
	$(PYTHON) -m $(NAME) compose -p demo_song --prompt "Create a simple gospel song with organ, bass, and drums"
	$(PYTHON) -m $(NAME) arrange -p demo_song
	$(PYTHON) -m $(NAME) orchestrate -p demo_song
	$(PYTHON) -m $(NAME) critique -p demo_song
	$(PYTHON) -m $(NAME) repair -p demo_song
	@echo "Demo project created!"
	@echo "Run 'maestro status -p demo_song' to see the pipeline status"

# Show project status
status:
	$(PYTHON) -m $(NAME) project list
	@echo ""
	$(PYTHON) -m $(NAME) status -p demo_song 2>/dev/null || echo "No demo_song project"

# Initialize git repository (safe to run multiple times)
init-git:
	git init 2>/dev/null || true
	git add . 2>/dev/null || true
	@echo "Git repository initialized"

# Create .env from .env.example if it doesn't exist
init-env:
	[ -f .env ] || cp .env.example .env
	@echo "Environment file created from .env.example"
	@echo "Please edit .env with your API keys and settings"
