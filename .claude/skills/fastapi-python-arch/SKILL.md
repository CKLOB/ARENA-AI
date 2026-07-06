---
name: fastapi-python-arch
description: Architecture guide for this Python/FastAPI service.
---

# FastAPI + Python Architecture

Keep the app boring until requirements force structure.

## Current Shape

- `main.py` owns the FastAPI app.
- `requirements.txt` pins runtime dependencies.
- `compose.yml` owns local backing services only.

## When Adding Code

- Keep route handlers thin.
- Move reusable provider/model/business logic into plain Python modules.
- Use Pydantic models at trust boundaries.
- Do not add packages for small stdlib jobs.
- Add the smallest runnable check for non-trivial logic.
