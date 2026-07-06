---
name: database-schema
description: Postgres schema guidance for this Python service. Use only when DB tables or persistence are actually being added.
---

# Database Schema Guide

This repo currently has no application DB layer. Do not add schema tooling until a real persistence requirement exists.

## Defaults When Needed

- Postgres for local/dev parity.
- Alembic for migrations if SQLAlchemy is introduced.
- `snake_case` table and column names.
- `created_at` and `updated_at` timestamps on durable domain tables.
- Explicit indexes for frequent lookup predicates only.

Keep schema changes in the same PR as the code that uses them.
