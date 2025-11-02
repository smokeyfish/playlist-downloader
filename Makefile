.PHONY: install run clean setup lint test

# Python settings
PYTHON := python3
VENV := .venv
UV := uv

# Installation and setup
install: $(VENV)
	$(UV) pip install -e ".[dev]"
	$(UV)/pre-commit install

$(VENV):
	$(PYTHON) -m uv venv

setup: install

# Running the application
run:
	$(UV) run src/playlist_downloader/__init__.py

# Development tools
lint:
	$(UV) run black src/
	$(UV) run isort src/
# Cleaning
clean:
	rm -rf $(VENV)
	rm -rf *.egg-info
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf build dist
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Help target
help:
	@echo "Available commands:"
	@echo "  make install    - Install the project and dependencies"
	@echo "  make setup     - Alias for install"
	@echo "  make run       - Run the playlist downloader with uv"
	@echo "  make lint      - Format code with Black"
	@echo "  make clean     - Remove virtual environment and cache files"
	@echo "  make help      - Show this help message"

# Default target
.DEFAULT_GOAL := help