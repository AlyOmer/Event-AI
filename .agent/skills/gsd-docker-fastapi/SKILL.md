---
name: gsd-docker-fastapi
description: |
  Containerize Python/FastAPI applications from hello world to production deployments.
  This skill should be used when users want to create Dockerfiles, docker-compose.yml files, or production-ready container setups for FastAPI projects.
---

# Docker FastAPI Containerization

Containerize Python/FastAPI applications with production-grade reliability, security, and caching.

## Before Implementation

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Codebase** | App entry point (e.g., `main:app`), dependency file (`requirements.txt`, `Pipfile`, `pyproject.toml`, `uv`), python version |
| **Conversation** | User's deployment target (AWS, Kubernetes, simple VPS), expected scale |
| **Skill References** | `references/docker-patterns.md` for production best practices |
| **User Guidelines** | Required base image preferences, specific environment variables |

Ensure all required context is gathered before implementing.
Only ask user for THEIR specific requirements (domain expertise is in this skill).

## Discovery & Requirements Gathering

Before writing the `Dockerfile` or `docker-compose.yml`:
1. **Identify the App structure:** Where does the FastAPI instance live? (e.g., `src/main.py` -> `src.main:app`).
2. **Identify Dependencies:** Are they using `pip`, `poetry`, or `uv`? This affects the Dockerfile build process.
3. **Determine Scale:** Ask the user if this is a simple "hello world" setup, or a production deployment requiring `gunicorn` + worker management.

## Implementation Steps

### 1. Create the Dockerfile
Generate a `Dockerfile` following the guidelines in `references/docker-patterns.md`. Ensure you:
- Use a slim, specific base image.
- Configure dependency caching correctly (copy requirements, install, then copy source).
- Run as a non-root user.
- Select the right startup command (`fastapi run` or `gunicorn`).

### 2. Create docker-compose.yml (Optional but recommended)
If the user requests it or it fits their workflow, generate a `docker-compose.yml` to define the service, load environment variables, and map ports. Example:

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=production
    restart: unless-stopped
```

### 3. Verification & Checklist
Before finishing, verify:
- [ ] Dependencies are copied BEFORE the application code to optimize caching.
- [ ] The `CMD` uses the "exec form" (JSON array) to correctly handle signals.
- [ ] A non-root user is defined and activated via `USER <name>`.
- [ ] `pip install` uses `--no-cache-dir`.

## References
Consult `references/docker-patterns.md` for detailed Dockerfile patterns and best practices.
