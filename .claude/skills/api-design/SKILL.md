---
name: api-design
description: FastAPI API design guide for routes, request/response schemas, status codes, and error behavior.
---

# FastAPI API Design

Use this when adding or reviewing API endpoints.

## Rules

- Keep routes resource-oriented and versionable when a public contract exists.
- Put request/response shapes in Pydantic models when they are reused or non-trivial.
- Return explicit status codes for create/delete/error paths.
- Keep external AI/provider calls behind a service function, not inside route handlers.
- Do not change an API contract without updating matching docs or examples if they exist.

## Checks

```bash
python -m py_compile main.py
python -c "from main import app; assert app"
```
