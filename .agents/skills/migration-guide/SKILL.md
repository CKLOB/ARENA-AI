---
name: migration-guide
description: Migration guide for future DB changes in this Python service.
---

# Migration Guide

Use only after persistence exists.

## Order

1. Add or update SQLAlchemy models.
2. Add Alembic migration.
3. Update service/repository code.
4. Add or update tests.
5. Verify upgrade and downgrade when downgrade is supported.

Do not rely on auto-generated migrations without reading the generated SQL.
