# Makefile for workspace_fs package CI
# Author: DevArchitect-GPT
# Purpose: Automate local CI checks for quality assurance

.PHONY: help install test lint security coverage clean ci all

# Default target shows available commands
help:
	@echo "Available targets:"
	@echo "  install   - Install dependencies with Poetry"
	@echo "  test      - Run pytest with coverage"
	@echo "  lint      - Run ruff linting"
	@echo "  security  - Run bandit security analysis"
	@echo "  coverage  - Generate and open coverage report"
	@echo "  clean     - Remove build artifacts and cache"
	@echo "  ci        - Run all CI checks (test + lint + security)"
	@echo "  all       - Full pipeline: install + ci + coverage"

# Install dependencies
install:
	@echo "🔧 Installing dependencies..."
	poetry install

# Run tests with coverage
test:
	@echo "🧪 Running tests with coverage..."
	poetry run pytest -v --cov=workspace_fs --cov-report=term-missing --cov-report=html

# Run linting
lint:
	@echo "🔍 Running ruff linting..."
	poetry run ruff check .
	poetry run ruff format --check .

# Run security analysis  
security:
	@echo "🔒 Running bandit security analysis..."
	poetry run bandit -r src/ -f json -o bandit-report.json || true
	poetry run bandit -r src/

# Generate and view coverage report
coverage: test
	@echo "📊 Opening coverage report..."
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	else \
		echo "Coverage report generated in htmlcov/index.html"; \
	fi

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf .coverage htmlcov/ .pytest_cache/ .ruff_cache/
	rm -f bandit-report.json
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Run all CI checks
ci: lint security test
	@echo "✅ All CI checks completed successfully!"

# Full pipeline
all: install ci coverage
	@echo "🎉 Full pipeline completed successfully!"
