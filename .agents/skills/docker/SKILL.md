---
name: docker
description: Docker and Docker Compose guide for this FastAPI/Python service.
---

# Docker Guide

Use the existing `compose.yml` before adding new Docker files.

## Compose

- Keep app containers out of dev compose unless explicitly requested.
- Prefer official images with pinned tags.
- Add healthchecks for stateful services.
- Use volumes only for data that must persist between restarts.

## Dockerfile

Add a Dockerfile only when deployment or app-container local dev needs it. If added, copy dependency manifests before source files for cache efficiency.
