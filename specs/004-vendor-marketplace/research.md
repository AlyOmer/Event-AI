# Phase 0 Research: Vendor Marketplace

**Date**: 2026-04-07  
**Feature**: 004-vendor-marketplace  
** Architect**: Claude (Sonnet 4.6)

## Objectives

Research best practices for:
- PostgreSQL full-text search and Trigram indexing for vendor discovery
- Image upload and storage using CDN (Cloudflare R2 or AWS S3)
- Vendor approval workflow patterns
- Rate limiting strategies for Node.js/Fastify
- Authorization design for multi-role marketplace

## Key Findings

### PostgreSQL Full-Text Search and Trigram

**Full-Text Search**: PostgreSQL provides `to_tsvector` and `to_tsquery` for linguistic search. Create GIN indexes on `to_tsvector('english', column)` for fast text search. Useful for matching words in vendor name/description with stemming.

**Trigram Similarity**: `pg_trgm` extension enables fuzzy matching using GIN or GiST indexes with `gin_trgm_ops`. Functions: `similarity(a, b)`, `%` operator, `word_similarity`. Good for partial matches, typos.

**Recommended Approach**: Combine both:
- Use `to_tsvector` for basic full-text search (AND/OR queries)
- Use Trigram for LIKE '%term%' patterns and fuzzy matching
- Use separate indexes: `CREATE INDEX ... USING gin(to_tsvector('english', business_name))` and `CREATE INDEX ... USING gin(business_name gin_trgm_ops)`

**Ranking**: Use `ts_rank` for full-text and `similarity()` for trigram; combine with weighting (name > description). Sort by rank + additional factors (rating, location match).

**Performance**: Test with realistic dataset; ensure indexes are used. Avoid `ILIKE '%...%'` without trigram index.

### Image Upload with CDN

**Pattern**: Use pre-signed URLs for direct client upload to object storage.

**Flow**:
1. Client requests upload URL from backend (with JWT auth, file type/size validation)
2. Backend generates a pre-signed PUT URL (S3) or uses R2's policy, with a short TTL (5 minutes) and size limit.
3. Client uploads file directly to CDN endpoint using `PUT` with pre-signed URL.
4. CDN returns success; client sends the resulting object URL (or just the filename) to backend to associate with vendor profile.

**Benefits**: Offloads bandwidth from backend, scalable, CDN caches images globally.

**Security**: Pre-signed URLs should have limited scope (bucket, key prefix, content-type). Validate file signatures (magic bytes) after upload if needed (CDN can trigger lambda validation). Enforce size limits upfront.

**Storage Choice**: Cloudflare R2 (S3-compatible, no egress fees) or AWS S3. Both work.

### Approval Workflow Patterns

**Typical flow**:
- Vendor creates/updates profile → status becomes `pending` (or generates an `ApprovalRequest`)
- Admin sees item in approval queue (list with key info)
- Admin clicks "Approve" or "Reject" (optionally with reason)
- System updates vendor status, logs decision, sends notification to vendor.
- For edits: only certain fields trigger re-approval (e.g., business name, primary category). Minor edits (description, portfolio) auto-approve.

**Implementation**:
- Add `approval_requests` table with status, timestamps, approver, snapshot.
- Backend service: `approval.service.ts` with functions: `listPending()`, `approve(requestId, adminUser)`, `reject(requestId, reason)`.
- Webhook/event after approval: update vendor's `approval_status`, `status` (if new vendor goes from pending to active), send email via notification service.
- Audit log: already in `approval_requests`; also log admin actions to separate audit table if needed.

**UI Considerations**:
- Admin approval queue should show: vendor name, type (new/edit), submitted date, priority indicators.
- Bulk actions possible later (not MVP).

### Rate Limiting

**Strategy**: Token bucket algorithm per identifier (IP + user ID combo).

**Library**: `fastify-rate-limit` for Fastify. Configure:
- `max`: 60 requests per minute for authenticated endpoints (public GET may be more)
- `keyGenerator`: function combining `req.user.id` (if logged in) and `req.ip`
- `skipOnError`: false (count errors too)

**Storage**: In-memory for single instance; for multiple instances, use Redis store (`fastify-rate-limit` supports Redis).

**Endpoints to limit**: All API routes. Possibly separate limits: registration endpoint stricter (5/min) to prevent account flooding.

**Response**: HTTP 429 with `Retry-After` header.

### Authorization (RBAC)

**Roles**:
- `user` (customer): read-only access to public vendor profiles and search; can create inquiries
- `vendor` (business): can create own vendor profile, edit own profile, upload portfolio; cannot access other vendors' data
- `admin`: full access to all vendor data, approval queue, category management

**Implementation**:
- JWT token contains `userId` and `role` (from NextAuth.js session).
- Backend middleware: `protect` verifies JWT; `authorize(role)` checks role.
- For vendor-owned resources: route handlers verify `vendor.user_id === req.user.id`.
- For admin routes: `authorize('admin')`.

**Enforcement**: Never rely on frontend hiding; backend checks every request.

## Decisions Summary

1. **Search**: PostgreSQL full-text + Trigram; no external service.
2. **Image storage**: Pre-signed URLs for direct CDN upload (Cloudflare R2 or S3).
3. **Approval**: Dedicated `approval_requests` table; admin service; status transitions.
4. **Rate limiting**: `fastify-rate-limit` with Redis for multi-instance.
5. **Authz**: Role-based with JWT claims; per-resource ownership checks.
6. **Indexes**: Add GIN/GIST for search performance; foreign key indexes; status indexes.
7. **API versioning**: `/api/v1/` prefix.

## Alternatives Considered

- **Search**: Algolia/Elastic – too expensive, adds infrastructure; rejected for MVP.
- **Image hosting**: Local filesystem storage – not scalable, no CDN; rejected.
- **Approval**: Simple status field on vendors only – insufficient audit trail; rejected.
- **Rate limiting**: Custom implementation – unnecessary when library exists; use `fastify-rate-limit`.

## References

- Constitution: Sections I (Monorepo), II (Tech Stack), IV (Databases), V (Testing), VI (API Contracts), VIII (Security), IX (Simplicity)
- Prisma Migrate docs: https://www.prisma.io/docs/concepts/components/prisma-migrate
- Fastify plugins: `fastify-rate-limit`, `@fastify/cookie`, `@fastify/jwt`
- PostgreSQL full-text: https://www.postgresql.org/docs/current/textsearch.html
- pg_trgm: https://www.postgresql.org/docs/current/pgtrgm.html

---

**Research Complete**: All uncertainties resolved; ready to proceed to data model and API contracts.
