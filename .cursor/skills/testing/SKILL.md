---
name: testing
description: AxiomPy testing standards and patterns. Use when writing tests, test fixtures, mock clients, or when the user asks about testing conventions or coverage requirements.
---

# AxiomPy Testing Standards

## Layout

- Tests: `tests/test_<module>.py`
- Framework: **pytest** with fixtures; group related tests in classes
- Target **80%+** coverage on touched modules (`pyproject.toml` sets `fail_under = 80`)

## Patterns

- **Settings:** valid inputs succeed; invalid inputs raise; defaults apply
- **Factories:** `create()` returns correct implementation per enum/type; `create_mock()` is usable; unknown types raise `ValueError`
- **Services / I/O:** happy path, boundaries, error paths; use **`unittest.mock.patch`** for external systems
- **Factories with mocks:** use `create_mock()` and assert call logs where the API records them

```python
import pytest
from unittest.mock import patch

class TestFeature:
    @pytest.fixture
    def service(self):
        with patch("axiompy.some.module.ClientFactory.create") as m:
            m.return_value = ...
            yield build_service()
```

## Running tests

```bash
pytest tests/ -v --cov=axiompy --cov-report=term-missing
```

See **`AGENTS.md`** for project-wide testing expectations.
