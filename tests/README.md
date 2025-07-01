# Test Suite

Struttura organizzata dei test seguendo i principi **DevArchitect-GPT**:

## 📁 Struttura

```
tests/
├── __init__.py              # Package documentation
├── README.md               # This file
├── unit/                   # Unit tests - single component testing
│   ├── __init__.py
│   └── test_secure_agent.py    # SecureAgent class tests
└── integration/            # Integration tests - end-to-end scenarios
    ├── __init__.py
    └── test_phase2_task1.py     # Phase 2 Task 1 complete workflow
```

## 🏗️ Architecture Principles

- **High Cohesion**: Each test module focuses on single component/functionality
- **Low Coupling**: Tests use dependency injection and mocking
- **Clear Separation**: Unit tests vs Integration tests
- **Clean Organization**: Following project structure conventions

## 📋 Test Categories

### Unit Tests (`tests/unit/`)

- Test individual components in isolation
- Fast execution
- Focused on single responsibility
- Use mocks for external dependencies

### Integration Tests (`tests/integration/`)

- Test complete workflows
- End-to-end scenarios
- Real component interactions
- Verify system behavior

## 🚀 Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run only unit tests
python -m pytest tests/unit/

# Run only integration tests
python -m pytest tests/integration/

# Run specific test file
python tests/integration/test_phase2_task1.py
```

## ✅ Best Practices

1. **Naming**: `test_<component_name>.py` for files, `test_<functionality>` for methods
2. **Structure**: Arrange-Act-Assert pattern
3. **Independence**: Each test should be independent
4. **Documentation**: Clear docstrings explaining what is being tested
5. **Coverage**: Aim for high coverage but focus on meaningful tests
