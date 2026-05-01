# Docker FastAPI Production Patterns

## 1. Dockerfile Best Practices

### Base Image
- **Always** use a specific base image tag (e.g., `python:3.12-slim`). Avoid `latest`.

### Caching and Dependencies
- Copy `requirements.txt` (or similar lock file) first, then run `pip install`, and finally copy the application source. This ensures Docker leverages layer caching effectively.
- Use `--no-cache-dir` with `pip install` to reduce the image size.

### Security and Permissions
- Never run your container processes as the `root` user in production.
- Create a dedicated non-root user (e.g., `myuser`), set correct permissions using `chown`, and use `USER myuser`.

### Multi-stage Builds
- For complex dependencies, use multi-stage builds to compile C extensions or other dependencies in a "builder" stage, then only copy the resulting compiled artifacts and installed packages to the final image.

## 2. Production Server Strategies

### Command vs Server
- **Option 1 (Simple/Managed scaling)**: Use the modern `fastapi run` CLI which is optimized for production. It uses `uvicorn` and handles basic workloads easily.
- **Option 2 (High Concurrency/Master Process)**: Use `gunicorn` with `uvicorn.workers.UvicornWorker`. This is the battle-tested standard for handling multiprocessing in Python web apps.
- Configure workers based on CPUs. Common rule: `(2 * CPU_CORES) + 1`.

## 3. Production Configuration

### Environment Variables
- Never hardcode secrets. Pass them at runtime via orchestration tools or `.env` files. Ensure they aren't built into the Docker image itself.
- Set `DEBUG=False` in production contexts.

### Orchestration & Proxies
- Place a reverse proxy like **Nginx** or **Traefik** in front of your FastAPI container to handle SSL/TLS termination, static files, and buffering.
- Define container health checks (e.g., calling `/health`).

### Example Production Dockerfile snippet

```dockerfile
# Start from slim Python image
FROM python:3.12-slim

# Create a non-root user
RUN useradd -m fastapiuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Secure permissions
RUN chown -R fastapiuser:fastapiuser /app
USER fastapiuser

# Run using the exec form to ensure signals (like SIGTERM) are passed properly
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "app.main:app"]
```
