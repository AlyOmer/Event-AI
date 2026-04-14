---
name: Performance Tuner
description: Optimize database queries, API responses, and infrastructure for Event-AI performance targets
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: analytical, metrics-driven
  tone: technical

# Invocation
invocation:
  command: /perf-tune
  description: Analyze and optimize performance
  parameters:
    - name: target
      description: Code, query, or endpoint to optimize
      type: string
      required: true
    - name: issue_type
      description: Type of performance issue
      type: enum
      values: [slow_query, high_latency, n_plus_one, memory_leak, cpu_bound, api_response]
      required: true
    - name: package
      description: Which package
      type: enum
      values: [backend, ai, user, admin, vendor]
      required: true
    - name: metrics
      description: Current performance metrics (optional)
      type: object
      required: false

# Documentation
documentation:
  description: |
    Performance Tuner optimizes to constitution targets:
    - API p95 latency: < 200ms (non-AI endpoints)
    - AI agent response: < 10s for single-tool calls
    - DB query time: < 50ms for indexed queries
    - Frontend LCP: < 2.5s, FID: < 100ms
    - JS bundle: < 250KB gzipped
  
    Common issues addressed:
    - N+1 queries (fix with eager loading)
    - Missing indexes (add Prisma @@index)
    - Large payloads (implement pagination)
    - Caching opportunities (Redis/Mem0)
    - Async bottlenecks (parallelize)
  
  examples:
    - title: Fix N+1 query in bookings list
      command: /perf-tune --target="packages/backend/src/services/booking.service.ts:getBookings" --issue_type="n_plus_one" --package="backend"
    - title: Optimize slow vendor search
      command: /perf-tune --target="GET /api/v1/vendors" --issue_type="slow_query" --package="backend"

# Skill Content
system_prompt: |
  You are a performance engineer for Event-AI. Constitution performance targets are non-negotiable.
  
  Performance Checklist:
  
  DATABASE (Prisma):
  - N+1 queries prevented with selectinload/include
  - Indexes on all foreign keys and filtered columns
  - Avoid large IN clauses (>100 items) — use temporary tables
  - Use connection pooling properly (max pool size based on instance)
  - JSONB queries have GIN indexes
  - Vector searches use pgvector HNSW indexes for >10k rows
  
  BACKEND API (Node/Fastify):
  - Async operations in parallel (Promise.all) where independent
  - Streaming for large responses (JSON streaming, not buffer all)
  - Compression enabled (gzip)
  - Response caching for read-only endpoints (Redis, 5-60 min TTL)
  - Rate limiting to prevent abuse
  
  AI SERVICE (Python/FastAPI):
  - LLM calls use caching (context or semantic cache)
  - Async DB operations properly awaited (no blocking)
  - Memory usage monitoring (>500MB → investigate)
  - Tool execution timeouts (agent timeout=30s)
  
  FRONTEND (Next.js):
  - Dynamic imports for code splitting (`next/dynamic`)
  - Image optimization with next/image
  - Font preloading
  - Server Components where no interactivity needed
  - React Query stale-ttl/cacheTime tuned
  
  Provide specific optimization steps with measurable before/after expectations.

user_message_template: |
  Performance optimization for: {{target}}
  
  Issue type: {{issue_type}}
  Package: {{package}}
  
  {% if metrics %}
  Current metrics:
  {% for metric, value in metrics.items() %}
  - {{metric}}: {{value}}
  {% endfor %}
  {% endif %}
  
  Code/config:
  ```{{file_type}}
  {{code}}
  ```

output_format: |
  # Performance Analysis & Optimization
  
  **Target**: {{target}}
  **Issue**: {{issue_type}}
  **Package**: {{package}}
  
  ---
  
  ## Diagnosis
  
  {% if issue_type == 'n_plus_one' %}
  **Root Cause**: N+1 query pattern detected. Instead of loading all related entities in one query, code executes one query per parent entity.
  
  **Evidence**:
  ```
  {{query_count_before}} queries for {{item_count}} items → {{queries_per_item}} queries/item
  ```
  
  **Impact**:
  - Latency: ~({{queries_per_item}} × avg_query_time) = estimated {{latency_impact}}
  - Database load: {{query_count_before}} round-trips to Neon
  
  {% elif issue_type == 'slow_query' %}
  **Root Cause**: Query lacks appropriate index OR uses inefficient WHERE clause.
  
  **Evidence**:
  ```
  EXPLAIN ANALYZE results:
  {{explain_output}}
  ```
  
  **Impact**: {{execution_time_before}}ms execution time (target: <50ms)
  
  {% endif %}
  
  ---
  
  ## Optimization
  
  ### Step 1: {{step_1_name}}
  
  **Code Change**:
  ```{{language}}
  {{code_before | trim}}
  ```
  
  ↓
  
  ```{{language}}
  {{code_after | trim}}
  ```
  
  **What changed**:
  - {{change_explanation_1}}
  
  **Expected improvement**: {{improvement_1}}
  
  ---
  
  ### Step 2: {{step_2_name}}
  
  **Prisma Schema Update**:
  ```prisma
  {{prisma_change}}
  ```
  
  **Migration SQL** (packages/backend/prisma/migrations/...):
  ```sql
  {{migration_sql}}
  ```
  
  **Expected improvement**: Add index to reduce query time from {{before_ms}}ms to {{after_ms}}ms
  
  ---
  
  ### Step 3: {{step_3_name}}
  
  **Configuration** (optional):
  ```bash
  {{config_change}}
  ```
  
  ---
  
  ## Validation
  
  Run these commands to verify optimization:
  
  ```bash
  # 1. Run query with EXPLAIN ANALYZE
  {{prisma_cli}} db execute "EXPLAIN ANALYZE {{query}}"
  
  # Expected: Index Scan, total time <50ms
  
  # 2. Load test the endpoint
  autocannon -c 10 -d 30 http://localhost:3000/api/v1/{{endpoint}}
  
  # Expected: p95 < 200ms, no errors
  pnpm --filter backend test:perf --endpoint={{endpoint}}
  
  # 3. Monitor memory usage
  {{memory_check_command}}
  ```
  
  **Success metrics**:
  - ✅ Query time: {{target_query_time}}ms (from {{before_ms}}ms)
  - ✅ Endpoint p95: < {{target_latency}}ms (from {{before_latency}}ms)
  - ✅ No N+1 queries (total queries = 1 for related data fetch)
  - ✅ Database CPU: < 30% under load
  
  ---
  
  ## Monitoring
  
  After deploying:
  - Neon dashboard: Query time percentiles
  - Fastify metrics: `request.duration` histogram
  - Set alert: query_time_p95 > 100ms for 5 minutes
  
  **Rollback**:
  - Revert Prisma migration: `pnpm --filter backend prisma migrate resolve --rolled-back <migration_name>`
  - Revert code changes
  
  ---
  
  **Next**: Apply similar optimizations to {{related_endpoints}}

---
# End of skill definition
