---
inclusion: manual
---

# Docker Expert

Advanced Docker containerization expertise: multi-stage builds, image optimization, container security, Docker Compose orchestration, and production deployment patterns.

## When Invoked

First, check if the issue is outside Docker scope:
- Kubernetes orchestration → kubernetes-expert
- GitHub Actions CI/CD → github-actions-expert
- AWS ECS/Fargate → devops-expert
- Complex database persistence → database-expert

## Analysis Approach

```bash
# Detect environment
docker --version && docker info | grep -E "Server Version|Storage Driver"
find . -name "Dockerfile*" -type f | head -10
find . -name "*compose*.yml" -o -name "*compose*.yaml" | head -5
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>/dev/null
```

Adapt approach to match existing patterns, base images, and orchestration setup.

## Core Patterns

### Optimized Multi-Stage Build
```dockerfile
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build && npm prune --production

FROM node:18-alpine AS runtime
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
WORKDIR /app
COPY --from=deps --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=build --chown=nextjs:nodejs /app/dist ./dist
USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1
CMD ["node", "dist/index.js"]
```

### Security Hardening
```dockerfile
FROM node:18-alpine
RUN addgroup -g 1001 -S appgroup && adduser -S appuser -u 1001 -G appgroup
WORKDIR /app
COPY --chown=appuser:appgroup package*.json ./
RUN npm ci --only=production
COPY --chown=appuser:appgroup . .
USER 1001
```

### Production Compose
```yaml
version: '3.8'
services:
  app:
    build: { context: ., target: production }
    depends_on:
      db: { condition: service_healthy }
    networks: [frontend, backend]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits: { cpus: '0.5', memory: 512M }
        reservations: { cpus: '0.25', memory: 256M }
  db:
    image: postgres:15-alpine
    volumes: [postgres_data:/var/lib/postgresql/data]
    networks: [backend]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      retries: 5
networks:
  frontend:
  backend: { internal: true }
volumes:
  postgres_data:
```

### Build Cache Optimization
```dockerfile
RUN --mount=type=cache,target=/root/.npm npm ci --only=production
```

### Build-Time Secrets
```dockerfile
RUN --mount=type=secret,id=api_key API_KEY=$(cat /run/secrets/api_key) && ...
```

### Multi-Architecture Builds
```bash
docker buildx create --name multiarch-builder --use
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:latest --push .
```

## Validation
```bash
docker build --no-cache -t test-build .
docker scout quickview test-build 2>/dev/null
docker-compose config && echo "Compose config valid"
```

## Review Checklist

- [ ] Dependencies copied before source code (layer caching)
- [ ] Multi-stage builds separate build and runtime
- [ ] Non-root user with specific UID/GID
- [ ] Secrets not in ENV vars or image layers
- [ ] Health checks implemented
- [ ] Resource limits defined
- [ ] .dockerignore comprehensive
- [ ] Development targets separate from production
- [ ] Internal networks for backend services

## Common Issues

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Slow builds | Poor layer ordering, large context | Multi-stage, .dockerignore, dep caching |
| Security scan failures | Outdated images, root execution | Regular updates, non-root config |
| Images over 1GB | Build tools in production | Distroless, multi-stage, artifact selection |
| Service comm failures | Missing networks, DNS errors | Custom networks, health checks |
| Hot reload failures | Volume mounting issues | Dev-specific targets, proper volume strategy |
