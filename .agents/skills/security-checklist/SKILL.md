---
name: security-checklist
description: Security checklist for Python/FastAPI changes.
---

# Security Checklist

- No secrets committed outside `.env.example`.
- No API keys, tokens, or passwords logged.
- External inputs validated with Pydantic or explicit checks.
- Provider responses treated as untrusted data.
- Network calls have clear error handling.
- CORS/auth changes are reviewed explicitly.

Useful searches:

```bash
rg -n "password|secret|token|api[_-]?key|sk-" .
rg -n "print\\(|logger\\..*token|logger\\..*secret" .
```
