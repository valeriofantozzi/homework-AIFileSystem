# CI Configuration for workspace_fs Package

## Overview

This document describes the local CI configuration for the `workspace_fs` package, implementing **high-cohesion** and **low-coupling** development practices with automated quality gates.

## Architecture

The CI system follows SOLID principles with three main components:

- **Makefile**: Simple target-based automation (high cohesion per target)
- **ci_validate.py**: Comprehensive validation script with detailed reporting
- **pyproject.toml**: Centralized tool configuration (dependency inversion)

## Available Commands

### Quick Commands (Makefile)

```bash
# Show all available targets
make help

# Run all CI checks (lint + security + test)
make ci

# Full pipeline (install + CI + coverage report)
make all

# Individual checks
make lint      # Run ruff linting
make security  # Run bandit security analysis
make test      # Run pytest with coverage
make coverage  # Generate and open coverage report
make clean     # Remove build artifacts
```

### Detailed Validation (Python Script)

```bash
# Run comprehensive CI with detailed output
python ci_validate.py

# With proper exit codes for automation
echo $?  # 0 = success, 1 = failure
```

## Quality Gates

### 1. Code Style & Linting (ruff)

- **Format checking**: Ensures consistent code formatting
- **Style rules**: Enforces Python best practices
- **Type annotations**: Modern Python 3.10+ style (list vs List)
- **Import sorting**: Clean, organized imports

**Configuration**: See `[tool.ruff]` in `pyproject.toml`

### 2. Security Analysis (bandit)

- **Vulnerability scanning**: Detects common security issues
- **Dependency checking**: Identifies problematic packages
- **Configuration**: Low-level warnings only (`-ll`)

**Output**: JSON report in `bandit-report.json`

### 3. Test Coverage (pytest + pytest-cov)

- **Minimum threshold**: 80% coverage (configurable)
- **HTML reports**: Generated in `htmlcov/` directory
- **Missing lines**: Clearly identified for focused testing

**Current status**: 53% coverage (acceptable for API-only phase)

## Integration Points

### Pre-commit Hooks (Recommended)

```bash
# Install pre-commit hooks
pip install pre-commit
echo "make lint" > .pre-commit-config.yaml
```

### IDE Integration

- **VSCode**: Configure workspace settings for ruff
- **PyCharm**: Enable pytest and coverage integration
- **Terminal**: Use `make ci` for quick validation

### GitHub Actions (Template Available)

See `.github-actions-example.yml` for CI/CD pipeline setup.

## Development Workflow

1. **Write code** following API contracts
2. **Run `make lint`** to fix style issues
3. **Run `make test`** to verify functionality
4. **Run `make ci`** before committing
5. **Review coverage** with `make coverage`

## Architecture Compliance

✅ **High Cohesion**: Each tool has a single responsibility
✅ **Low Coupling**: Tools are independently configurable
✅ **SOLID**: Dependency inversion via configuration
✅ **Clean Code**: Automated enforcement of style rules

## Troubleshooting

### Linting Failures

```bash
# Auto-fix most issues
poetry run ruff check . --fix
poetry run ruff format .
```

### Test Failures

```bash
# Run tests with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_api.py -v
```

### Coverage Issues

```bash
# Generate detailed coverage report
poetry run pytest --cov=workspace_fs --cov-report=html
open htmlcov/index.html
```

## Next Steps

As the package implementation progresses:

1. **Coverage will increase** with behavior tests (Tasks 2-4)
2. **More security rules** may be added for production use
3. **Performance tests** could be integrated for tool operations

The CI configuration is designed to scale with the project while maintaining quality gates throughout the development cycle.
