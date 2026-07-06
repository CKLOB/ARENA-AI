---
name: pytest-guide
description: Pytest and FastAPI TestClient guidance for this repo.
---

# Pytest Guide

Use pytest only when tests exist or the change needs a real regression check.

## Patterns

- Use plain `assert`.
- Use FastAPI `TestClient` for endpoint behavior.
- Keep fixtures local until shared setup is repeated.
- Mock external provider calls at the module boundary.

## Minimal Example

```python
from fastapi.testclient import TestClient
from main import app


def test_health():
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
```
