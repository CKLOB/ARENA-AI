---
name: test
description: Run the smallest useful Python check or test command and report results.
---

# Test Skill

## Selection

- If a specific pytest target is obvious, run it.
- If tests exist, run `pytest`.
- If no tests exist, run:

```bash
.venv/bin/python -m py_compile main.py
.venv/bin/python -c "from main import app; assert app"
```

Use `python` instead of `.venv/bin/python` only when `.venv` is unavailable.
